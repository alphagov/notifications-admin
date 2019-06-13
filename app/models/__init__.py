from flask import abort


class JSONModel():

    ALLOWED_PROPERTIES = set()

    def __init__(self, _dict):
        # in the case of a bad request _dict may be `None`
        self._dict = _dict or {}

    def __bool__(self):
        return self._dict != {}

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


class InviteTokenError(Exception):
    pass
