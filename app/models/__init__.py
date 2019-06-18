from abc import ABC, abstractmethod
from collections.abc import Sequence

from flask import abort


class JSONModel():

    ALLOWED_PROPERTIES = set()

    def __init__(self, _dict):
        # in the case of a bad request _dict may be `None`
        self._dict = _dict or {}

    def __bool__(self):
        return self._dict != {}

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __getattr__(self, attr):
        if attr in self.ALLOWED_PROPERTIES:
            return self._dict[attr]
        raise AttributeError('`{}` is not a {} attribute'.format(
            attr,
            self.__class__.__name__.lower(),
        ))

    def _get_by_id(self, things, id):
        try:
            return next(thing for thing in things if thing['id'] == str(id))
        except StopIteration:
            abort(404)


class ModelList(ABC, Sequence):

    @property
    @abstractmethod
    def client():
        pass

    @property
    @abstractmethod
    def model():
        pass

    def __init__(self):
        self.items = self.client()

    def __getitem__(self, index):
        return self.model(self.items[index])

    def __len__(self):
        return len(self.items)

    def __add__(self, other):
        return list(self) + list(other)


class InviteTokenError(Exception):
    pass
