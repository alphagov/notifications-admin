from flask import current_app


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


class InvalidPhoneError(Exception):
    def __init__(self, message):
        self.message = message


def validate_phone_number(number):
    if number == current_app.config['TWILIO_TEST_NUMBER']:
        return number

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
