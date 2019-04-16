import re

from notifications_utils.field import Field
from notifications_utils.recipients import (
    InvalidEmailError,
    validate_email_address,
)
from notifications_utils.sanitise_text import SanitiseGSM
from wtforms import ValidationError
from wtforms.validators import Email

from app import formatted_list
from app.main._blacklisted_passwords import blacklisted_passwords
from app.utils import Spreadsheet, is_gov_user


class Blacklist:
    def __init__(self, message=None):
        if not message:
            message = 'Password is blacklisted.'
        self.message = message

    def __call__(self, form, field):
        if field.data in blacklisted_passwords:
            raise ValidationError(self.message)


class CsvFileValidator:

    def __init__(self, message='Not a csv file'):
        self.message = message

    def __call__(self, form, field):
        if not Spreadsheet.can_handle(field.data.filename):
            raise ValidationError("{} isn’t a spreadsheet that Notify can read".format(field.data.filename))


class ValidGovEmail:

    def __call__(self, form, field):

        if field.data == '':
            return

        from flask import url_for
        message = (
            'Enter a government email address.'
            ' If you think you should have access'
            ' <a href="{}">contact us</a>').format(url_for('main.support'))
        if not is_gov_user(field.data.lower()):
            raise ValidationError(message)


class ValidEmail(Email):

    def __init__(self):
        super().__init__('Enter a valid email address')

    def __call__(self, form, field):

        if field.data == '':
            return

        try:
            validate_email_address(field.data)
        except InvalidEmailError:
            raise ValidationError(self.message)

        return super().__call__(form, field)


class NoCommasInPlaceHolders:

    def __init__(self, message='You can’t put commas between double brackets'):
        self.message = message

    def __call__(self, form, field):
        if ',' in ''.join(Field(field.data).placeholders):
            raise ValidationError(self.message)


class OnlyGSMCharacters:
    def __call__(self, form, field):
        non_gsm_characters = sorted(list(SanitiseGSM.get_non_compatible_characters(field.data)))
        if non_gsm_characters:
            raise ValidationError(
                'You can’t use {} in text messages. {} won’t show up properly on everyone’s phones.'.format(
                    formatted_list(non_gsm_characters, conjunction='or', before_each='', after_each=''),
                    ('It' if len(non_gsm_characters) == 1 else 'They')
                )
            )


class LettersNumbersAndFullStopsOnly:

    regex = re.compile(r'^[a-zA-Z0-9\s\.]+$')

    def __init__(self, message='Use letters and numbers only'):
        self.message = message

    def __call__(self, form, field):
        if field.data and not re.match(self.regex, field.data):
            raise ValidationError(self.message)


class DoesNotStartWithDoubleZero:

    def __init__(self, message="Can't start with 00"):
        self.message = message

    def __call__(self, form, field):
        if field.data and field.data.startswith("00"):
            raise ValidationError(self.message)
