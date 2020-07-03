from abc import abstractmethod

from flask import abort
from notifications_utils.serialised_model import (
    SerialisedModel,
    SerialisedModelCollection,
)


class JSONModel(SerialisedModel):

    def __init__(self, _dict):
        # in the case of a bad request _dict may be `None`
        self._dict = _dict or {}

    def __bool__(self):
        return self._dict != {}

    def __hash__(self):
        return hash(self.id)

    def __dir__(self):
        return super().__dir__() + list(sorted(self.ALLOWED_PROPERTIES))

    def __eq__(self, other):
        return self.id == other.id

    def __getattribute__(self, attr):
        # Eventually we should remove this custom implementation in
        # favour of looping over self.ALLOWED_PROPERTIES in __init__

        try:
            return super().__getattribute__(attr)
        except AttributeError as e:
            # Re-raise any `AttributeError`s that are not directly on
            # this object because they indicate an underlying exception
            # that we don’t want to swallow
            if str(e) != "'{}' object has no attribute '{}'".format(
                self.__class__.__name__, attr
            ):
                raise e

        if attr in super().__getattribute__('ALLOWED_PROPERTIES'):
            return super().__getattribute__('_dict')[attr]

        raise AttributeError((
            "'{}' object has no attribute '{}' and '{}' is not a field "
            "in the underlying JSON"
        ).format(
            self.__class__.__name__, attr, attr
        ))

    def _get_by_id(self, things, id):
        try:
            return next(thing for thing in things if thing['id'] == str(id))
        except StopIteration:
            abort(404)


class ModelList(SerialisedModelCollection):

    @property
    @abstractmethod
    def client_method(self):
        pass

    def __init__(self, *args):
        self.items = self.client_method(*args)
