from flask import session
from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email, Length, Regexp

from app.main.encryption import checkpw
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
verify_code = "[\\d]{5}$"


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
        validate_code(self.sms_code, session['sms_code'])


class VerifyForm(Form):
    sms_code = StringField("Text message confirmation code",
                           validators=[DataRequired(message='SMS code can not be empty'),
                                       Regexp(regex=verify_code, message='Code must be 5 digits')])
    email_code = StringField("Email confirmation code",
                             validators=[DataRequired(message='Email code can not be empty'),
                                         Regexp(regex=verify_code, message='Code must be 5 digits')])

    def validate_email_code(self, a):
        validate_code(self.email_code, session['email_code'])

    def validate_sms_code(self, a):
        validate_code(self.sms_code, session['sms_code'])


def validate_code(field, code):
    if field.data is not None:
        if checkpw(str(field.data), code) is False:
            field.errors.append('Code does not match')
            return False
        else:
            return True
    else:
        return True
