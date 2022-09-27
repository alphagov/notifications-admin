from abc import ABC, abstractmethod
from functools import total_ordering

from flask import abort
from notifications_utils.serialised_model import (
    SerialisedModel,
    SerialisedModelCollection,
)


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
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}(<{self.id}>)"

    def __lt__(self, other):
        return (getattr(self, self.__sort_attribute__).lower()) < (getattr(other, self.__sort_attribute__).lower())

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class JSONModel(SerialisedModel, SortingAndEqualityMixin):
    def __init__(self, _dict):
        # in the case of a bad request _dict may be `None`
        self._dict = _dict or {}
        for property in self.ALLOWED_PROPERTIES:
            if property in self._dict:
                setattr(self, property, self._dict[property])

    def __bool__(self):
        return self._dict != {}

    def _get_by_id(self, things, id):
        try:
            return next(thing for thing in things if thing["id"] == str(id))
        except StopIteration:
            abort(404)


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
