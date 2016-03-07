import re

from functools import wraps
from flask import (abort, session)

from utils.process_csv import get_recipient_from_row, first_column_heading


class BrowsableItem(object):
    """
    Maps for the template browse-list.
    """

    def __init__(self, item, *args, **kwargs):
        self._item = item
        super(BrowsableItem, self).__init__()

    @property
    def title(self):
        pass

    @property
    def link(self):
        pass

    @property
    def hint(self):
        pass

    @property
    def destructive(self):
        pass


def user_has_permissions(*permissions, or_=False):
    def wrap(func):
        @wraps(func)
        def wrap_func(*args, **kwargs):
            from flask_login import current_user
            if current_user and current_user.has_permissions(permissions, or_=or_):
                return func(*args, **kwargs)
            else:
                abort(403)
        return wrap_func
    return wrap
