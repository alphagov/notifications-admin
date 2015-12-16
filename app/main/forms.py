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
        codes = verify_codes_dao.get_codes(session['user_id'], 'sms')
        for code in codes:
            if validate_code(self.sms_code, code):
                return True


class VerifyForm(Form):
    sms_code = StringField("Text message confirmation code",
                           validators=[DataRequired(message='SMS code can not be empty'),
                                       Regexp(regex=verify_code, message='Code must be 5 digits')])
    email_code = StringField("Email confirmation code",
                             validators=[DataRequired(message='Email code can not be empty'),
                                         Regexp(regex=verify_code, message='Code must be 5 digits')])

    def validate_email_code(self, a):
        codes = verify_codes_dao.get_codes(session['user_id'], 'email')
        for code in codes:
            if validate_code(self.email_code, code):
                return True

    def validate_sms_code(self, a):
        codes = verify_codes_dao.get_codes(session['user_id'], 'sms')
        for code in codes:
            if validate_code(self.sms_code, code):
                return True


def validate_code(field, code):
    if code.expiry_datetime <= datetime.now():
        field.errors.append('Code has expired')
        return False
    if field.data is not None:
        if check_hash(field.data, code.code) is False:
            field.errors.append('Code does not match')
            return False
        else:
            return True
    else:
        return False


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
