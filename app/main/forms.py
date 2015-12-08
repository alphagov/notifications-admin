from flask import session
from flask_wtf import Form
from wtforms import StringField, PasswordField, IntegerField
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


class VerifyForm(Form):
    sms_code = StringField("Text message confirmation code",
                           validators=[DataRequired(message='SMS code can not be empty'),
                                       Length(min=5, max=5, message='Code must be 5 digits')])
    email_code = StringField("Email confirmation code",
                             validators=[DataRequired(message='Email code can not be empty'),
                                         Length(min=5, max=5, message='Code must be 5 digits')])

    def validate_email_code(self, a):
        if self.email_code.data is not None:
            if checkpw(str(self.email_code.data), session['email_code']) is False:
                self.email_code.errors.append('Code does not match')
                return False
        else:
            return True

    def validate_sms_code(self, a):
        if self.sms_code.data is not None:
            if checkpw(str(self.sms_code.data), session['sms_code']) is False:
                self.sms_code.errors.append('Code does not match')
                return False
        else:
            return True
