import re
from wtforms import ValidationError
from notifications_utils.template import Template
from app.utils import Spreadsheet


class Blacklist(object):
    def __init__(self, message=None):
        if not message:
            message = 'Password is blacklisted.'
        self.message = message

    def __call__(self, form, field):
        if field.data in ['password1234', 'passw0rd1234']:
            raise ValidationError(self.message)


class CsvFileValidator(object):

    def __init__(self, message='Not a csv file'):
        self.message = message

    def __call__(self, form, field):
        if not Spreadsheet.can_handle(field.data.filename):
            raise ValidationError("{} isn’t a spreadsheet that Notify can read".format(field.data.filename))


class ValidEmailDomainRegex(object):

    def __call__(self, form, field):
        from flask import (current_app, url_for)
        message = (
            'Enter a central government email address.'
            ' If you think you should have access'
            ' <a href="{}">contact us</a>').format(url_for('main.feedback'))
        valid_domains = current_app.config.get('EMAIL_DOMAIN_REGEXES', [])
        email_regex = "[^\@^\s]+@([^@^\\.^\\s]+\.)*({})$".format("|".join(valid_domains))
        if not re.match(email_regex, field.data.lower()):
            raise ValidationError(message)


class NoCommasInPlaceHolders():

    def __init__(self, message='You can’t have commas in your fields'):
        self.message = message

    def __call__(self, form, field):
        if ',' in ''.join(Template({'content': field.data}).placeholders):
            raise ValidationError(self.message)
