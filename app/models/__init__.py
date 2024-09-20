from abc import ABC, abstractmethod
from datetime import datetime
from functools import total_ordering
from typing import Any

import pytz
from flask import abort
from notifications_utils.serialised_model import (
    SerialisedModel,
    SerialisedModelCollection,
)
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime


@total_ordering
class SortingAndEqualityMixin(ABC):
    @property
    @abstractmethod
    def __sort_attribute__(self):
        """
        Subclasses that want sorting to work must set this property to the
        string name of the attribute on which the instances should be
        sorted. For example 'email_address' or 'created_at' to sort on
        instance.email_address or instance.created_at respectively.
        """

    def __repr__(self):
        return f"{self.__class__.__name__}(<{self.id}>)"

    def __lt__(self, other):
        return (getattr(self, self.__sort_attribute__).lower()) < (getattr(other, self.__sort_attribute__).lower())

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class JSONModel(SerialisedModel, SortingAndEqualityMixin):

    ALLOWED_PROPERTIES = set()  # This is deprecated

    def __new__(cls, *args, **kwargs):
        for parent in cls.__mro__:
            cls.__annotations__ = getattr(parent, "__annotations__", {}) | cls.__annotations__
        return super().__new__(cls)

    def __init__(self, _dict):
        # in the case of a bad request _dict may be `None`
        self._dict = _dict or {}
        for property, type_ in self.__annotations__.items():
            if property in self._dict:
                value = self.coerce_value_to_type(self._dict[property], type_)
                setattr(self, property, value)

    def __bool__(self):
        return self._dict != {}

    def _get_by_id(self, things, id):
        try:
            return next(thing for thing in things if thing["id"] == str(id))
        except StopIteration:
            abort(404)

    @staticmethod
    def coerce_value_to_type(value, type_):
        if type_ is Any or value is None:
            return value

        if issubclass(type_, datetime):
            return utc_string_to_aware_gmt_datetime(value).astimezone(pytz.utc)

        return type_(value)


class ModelList(SerialisedModelCollection):
    @property
    @abstractmethod
    def client_method(self):
        pass

    def __init__(self, *args):
        self.items = self.client_method(*args)


class PaginatedModelList(ModelList):
    response_key = "data"

    def __init__(self, *args, page=None, **kwargs):
        try:
            self.current_page = int(page)
        except TypeError:
            self.current_page = 1
        response = self.client_method(
            *args,
            **kwargs,
            page=self.current_page,
        )
        self.items = response[self.response_key]
        self.prev_page = response.get("links", {}).get("prev", None)
        self.next_page = response.get("links", {}).get("next", None)
