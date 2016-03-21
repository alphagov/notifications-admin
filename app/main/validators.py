import re
from wtforms import ValidationError
from datetime import datetime
from app.main.encryption import check_hash


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
        if not form.file.data.mimetype == 'text/csv':
            raise ValidationError(self.message)


class ValidEmailDomainRegex(object):

    def __call__(self, form, field):
        from flask import (current_app, url_for)
        message = (
            'Enter a central government email address.'
            ' If you think you should have access'
            ' <a href="{}">contact us</a>').format(
                "https://docs.google.com/forms/d/1AL8U-xJX_HAFEiQiJszGQw0PcEaEUnYATSntEghNDGo/viewform")
        valid_domains = current_app.config.get('EMAIL_DOMAIN_REGEXES', [])
        email_regex = "(^[^@^\\s]+@[^@^\\.^\\s]+(\\.[^@^\\.^\\s]*)*.({}))".format("|".join(valid_domains))
        if not re.match(email_regex, field.data):
            raise ValidationError(message)
