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


class ValidateUserCodes(object):
    def __init__(self,
                 expiry_msg='Code has expired',
                 invalid_msg='Code does not match',
                 code_type=None):
        self.expiry_msg = expiry_msg
        self.invalid_msg = invalid_msg
        self.code_type = code_type

    def __call__(self, form, field):
        # TODO would be great to do this sql query but
        # not couple those parts of the code.
        user_codes = getattr(form, 'user_codes', [])
        valid_code = False
        for code in user_codes:
            if check_hash(field.data, code.code) and self.code_type == code.code_type:
                if code.expiry_datetime <= datetime.now():
                    raise ValidationError(self.expiry_msg)
                else:
                    # Valid code
                    valid_code = True
                    break
        if not valid_code:
            raise ValidationError(self.invalid_msg)
