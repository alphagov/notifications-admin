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


class EmailList(object):
    def __init__(self, message, email_list=None):
        self.email_list = email_list
        self.message = message

    def __call__(self, form, field):
        from flask import current_app
        if self.email_list is None:
            self.email_list = current_app.config['EMAIL_DOMAIN_LIST']
        parts = field.data.split('@')
        if len(parts) == 2 and parts[1] not in self.email_list:
            raise ValidationError(self.message)
