import re

from functools import wraps
from flask import (abort, session, request, url_for)


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


def user_has_permissions(*permissions, admin_override=False, or_=False):
    def wrap(func):
        @wraps(func)
        def wrap_func(*args, **kwargs):
            from flask_login import current_user
            if current_user and current_user.has_permissions(permissions=permissions,
                                                             admin_override=admin_override, or_=or_):
                return func(*args, **kwargs)
            else:
                abort(403)
        return wrap_func
    return wrap


def get_errors_for_csv(recipients, template_type):

    errors = []

    missing_column_headers = list(recipients.missing_column_headers)

    if len(missing_column_headers) == 1:
        errors.append("add a column called ‘{}’".format("".join(missing_column_headers)))
    elif len(missing_column_headers) == 2:
        errors.append("add 2 columns, ‘{}’".format("’ and ‘".join(missing_column_headers)))
    elif len(missing_column_headers) > 2:
        errors.append(
            "add columns called ‘{}’, and ‘{}’".format(
                "’, ‘".join(missing_column_headers[0:-1]),
                missing_column_headers[-1]
            )
        )

    if recipients.rows_with_bad_recipients:
        number_of_bad_recipients = len(list(recipients.rows_with_bad_recipients))
        if 'sms' == template_type:
            if 1 == number_of_bad_recipients:
                errors.append("fix 1 phone number")
            else:
                errors.append("fix {} phone numbers".format(number_of_bad_recipients))
        elif 'email' == template_type:
            if 1 == number_of_bad_recipients:
                errors.append("fix 1 email address")
            else:
                errors.append("fix {} email addresses".format(number_of_bad_recipients))

    if recipients.rows_with_missing_data:
        number_of_rows_with_missing_data = len(list(recipients.rows_with_missing_data))
        if 1 == number_of_rows_with_missing_data:
            errors.append("fill in 1 empty cell")
        else:
            errors.append("fill in {} empty cells".format(number_of_rows_with_missing_data))

    return errors


def get_page_from_request():
    if 'page' in request.args:
        try:
            return int(request.args['page'])
        except ValueError:
            return None
    else:
        return 1


def generate_previous_next_dict(view, view_dict, page, title, label):
    return {
        'url': url_for(view, page=page, **view_dict),
        'title': title,
        'label': label
    }
