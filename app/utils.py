import re

from functools import wraps
from flask import (abort, session)


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


class InvalidEmailError(Exception):
    def __init__(self, message):
        self.message = message


class InvalidPhoneError(Exception):
    def __init__(self, message):
        self.message = message


def validate_phone_number(number):
    sanitised_number = number.replace('(', '')
    sanitised_number = sanitised_number.replace(')', '')
    sanitised_number = sanitised_number.replace(' ', '')
    sanitised_number = sanitised_number.replace('-', '')

    if sanitised_number.startswith('+'):
        sanitised_number = sanitised_number[1:]

    valid_prefixes = ['07', '447', '4407', '00447']
    if not sum(sanitised_number.startswith(prefix) for prefix in valid_prefixes):
        raise InvalidPhoneError('Must be a UK mobile number (eg 07700 900460)')

    for digit in sanitised_number:
        try:
            int(digit)
        except(ValueError):
            raise InvalidPhoneError('Must not contain letters or symbols')

    # Split number on first 7
    sanitised_number = sanitised_number.split('7', 1)[1]

    if len(sanitised_number) > 9:
        raise InvalidPhoneError('Too many digits')

    if len(sanitised_number) < 9:
        raise InvalidPhoneError('Not enough digits')

    return sanitised_number


def format_phone_number(number):
    import re
    if len(number) > 9:
        raise InvalidPhoneError('Too many digits')

    if len(number) < 9:
        raise InvalidPhoneError('Not enough digits')
    return '+447{}{}{}'.format(*re.findall('...', number))


def validate_email_address(email_address):
    if re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", email_address):
        return
    raise InvalidEmailError('Not a valid email address')


def validate_recipient(recipient, template_type):
    return {
        'email': validate_email_address,
        'sms': validate_phone_number
    }[template_type](recipient)


def user_has_permissions(*permissions, or_=False):
    def wrap(func):
        @wraps(func)
        def wrap_func(*args, **kwargs):
            # We are making the assumption that the user is logged in.
            from flask_login import current_user
            service_id = session.get('service_id', '')
            if current_user and current_user.has_permissions(service_id, permissions, or_=or_):
                return func(*args, **kwargs)
            else:
                abort(403)
        return wrap_func
    return wrap
