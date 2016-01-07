from datetime import datetime

from flask_wtf import Form
from wtforms import StringField, PasswordField, ValidationError
from wtforms.validators import DataRequired, Email, Length, Regexp
from app.main.dao import verify_codes_dao
from app.main.encryption import check_hash
from app.main.validators import Blacklist, ValidateUserCodes


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

    def __init__(self, existing_email_addresses, existing_mobile_numbers, *args, **kwargs):
        self.existing_emails = existing_email_addresses
        self.existing_mobiles = existing_mobile_numbers
        super(RegisterUserForm, self).__init__(*args, **kwargs)

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

    def validate_email_address(self, field):
        # Validate email address is unique.
        if field.data in self.existing_emails:
            raise ValidationError('Email address already exists')

    def validate_mobile_number(self, field):
        # Validate mobile number is unique
        # Code to re-added later
        # if field.data in self.existing_mobiles:
        #    raise ValidationError('Mobile number already exists')
        pass


class TwoFactorForm(Form):

    def __init__(self, user_codes, *args, **kwargs):
        '''
        Keyword arguments:
        user_codes -- List of user code objects which have the fields
        (code_type, expiry_datetime, code)
        '''
        self.user_codes = user_codes
        super(TwoFactorForm, self).__init__(*args, **kwargs)

    sms_code = StringField('sms code', validators=[DataRequired(message='Enter verification code'),
                                                   Regexp(regex=verify_code, message='Code must be 5 digits'),
                                                   ValidateUserCodes(code_type='sms')])


class VerifyForm(Form):

    def __init__(self, user_codes, *args, **kwargs):
        '''
        Keyword arguments:
        user_codes -- List of user code objects which have the fields
        (code_type, expiry_datetime, code)
        '''
        self.user_codes = user_codes
        super(VerifyForm, self).__init__(*args, **kwargs)

    sms_code = StringField("Text message confirmation code",
                           validators=[DataRequired(message='SMS code can not be empty'),
                                       Regexp(regex=verify_code, message='Code must be 5 digits'),
                                       ValidateUserCodes(code_type='sms')])
    email_code = StringField("Email confirmation code",
                             validators=[DataRequired(message='Email code can not be empty'),
                                         Regexp(regex=verify_code, message='Code must be 5 digits'),
                                         ValidateUserCodes(code_type='email')])


class EmailNotReceivedForm(Form):
    email_address = StringField('Email address', validators=[
        Length(min=5, max=255),
        DataRequired(message='Email cannot be empty'),
        Email(message='Please enter a valid email address'),
        Regexp(regex=gov_uk_email, message='Please enter a gov.uk email address')
    ])


class TextNotReceivedForm(Form):
    mobile_number = StringField('Mobile phone number', validators=[
        DataRequired(message='Please enter your mobile number'),
        Regexp(regex=mobile_number, message='Please enter a +44 mobile number')])


class AddServiceForm(Form):
    def __init__(self, service_names, *args, **kwargs):
        self.service_names = service_names
        super(AddServiceForm, self).__init__(*args, **kwargs)

    service_name = StringField(validators=[
        DataRequired(message='Please enter your service name')])

    def validate_service_name(self, a):
        if self.service_name.data in self.service_names:
            raise ValidationError('Service name already exists')
