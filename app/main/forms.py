from datetime import datetime

from flask import session
from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email, Length, Regexp

from app.main.dao import verify_codes_dao, services_dao
from app.main.encryption import check_hash
from app.main.validators import Blacklist


class LoginForm(Form):
    email_address = StringField('Email address', validators=[
        Length(min=5, max=255),
        DataRequired(message='Email cannot be empty'),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Please enter your password')
    ])


gov_uk_email = "(^[^@^\\s]+@[^@^\\.^\\s]+(\\.[^@^\\.^\\s]*)*.gov.uk)"
mobile_number = "^\\+44[\\d]{10}$"
verify_code = '^\d{5}$'


class RegisterUserForm(Form):
    name = StringField('Full name',
                       validators=[DataRequired(message='Name can not be empty')])
    email_address = StringField('Email address', validators=[
        Length(min=5, max=255),
        DataRequired(message='Email cannot be empty'),
        Email(message='Please enter a valid email address'),
        Regexp(regex=gov_uk_email, message='Please enter a gov.uk email address')
    ])
    mobile_number = StringField('Mobile phone number',
                                validators=[DataRequired(message='Please enter your mobile number'),
                                            Regexp(regex=mobile_number, message='Please enter a +44 mobile number')])
    password = PasswordField('Create a password',
                             validators=[DataRequired(message='Please enter your password'),
                                         Length(10, 255, message='Password must be at least 10 characters'),
                                         Blacklist(message='That password is blacklisted, too common')])


class TwoFactorForm(Form):
    sms_code = StringField('sms code', validators=[DataRequired(message='Please enter your code'),
                                                   Regexp(regex=verify_code, message='Code must be 5 digits')])

    def validate_sms_code(self, a):
        return validate_codes(self.sms_code, 'sms')


class VerifyForm(Form):
    sms_code = StringField("Text message confirmation code",
                           validators=[DataRequired(message='SMS code can not be empty'),
                                       Regexp(regex=verify_code, message='Code must be 5 digits')])
    email_code = StringField("Email confirmation code",
                             validators=[DataRequired(message='Email code can not be empty'),
                                         Regexp(regex=verify_code, message='Code must be 5 digits')])

    def validate_email_code(self, a):
        return validate_codes(self.email_code, 'email')

    def validate_sms_code(self, a):
        return validate_codes(self.sms_code, 'sms')


class EmailNotReceivedForm(Form):
    email_address = StringField('Email address', validators=[
        Length(min=5, max=255),
        DataRequired(message='Email cannot be empty'),
        Email(message='Please enter a valid email address'),
        Regexp(regex=gov_uk_email, message='Please enter a gov.uk email address')
    ])


class TextNotReceivedForm(Form):
    mobile_number = StringField('Mobile phone number',
                                validators=[DataRequired(message='Please enter your mobile number'),
                                            Regexp(regex=mobile_number, message='Please enter a +44 mobile number')])


class AddServiceForm(Form):
    service_name = StringField(validators=[DataRequired(message='Please enter your service name')])

    def validate_service_name(self, a):
        if services_dao.find_service_by_service_name(self.service_name.data) is not None:
            self.service_name.errors.append('Duplicate service name')
            return False
        else:
            return True


def validate_codes(field, code_type):
    codes = verify_codes_dao.get_codes(user_id=session['user_id'], code_type=code_type)
    is_valid = len([code for code in codes if validate_code(field, code)]) == 1
    if is_valid:
        field.errors.clear()
    return is_valid


def validate_code(field, code):
    if field.data and check_hash(field.data, code.code):
        if code.expiry_datetime <= datetime.now():
            field.errors.append('Code has expired')
            return False
        return True
    else:
        field.errors.append('Code does not match')
        return False
