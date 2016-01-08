from flask_wtf import Form
from wtforms import StringField, PasswordField, ValidationError
from wtforms.validators import DataRequired, Email, Length, Regexp
from app.main.validators import Blacklist, ValidateUserCodes


def email_address():
    gov_uk_email \
        = "(^[^@^\\s]+@[^@^\\.^\\s]+(\\.[^@^\\.^\\s]*)*.gov.uk)"
    return StringField('Email address', validators=[
        Length(min=5, max=255),
        DataRequired(message='Email cannot be empty'),
        Email(message='Enter a valid email address'),
        Regexp(regex=gov_uk_email, message='Enter a gov.uk email address')])


def mobile_number():
    mobile_number_regex = "^\\+44[\\d]{10}$"
    return StringField('Mobile phone number',
                       validators=[DataRequired(message='Mobile number can not be empty'),
                                   Regexp(regex=mobile_number_regex, message='Enter a +44 mobile number')])


def password():
    return PasswordField('Create a password',
                         validators=[DataRequired(message='Password can not be empty'),
                                     Length(10, 255, message='Password must be at least 10 characters'),
                                     Blacklist(message='That password is blacklisted, too common')])


def sms_code():
    verify_code = '^\d{5}$'
    return StringField('Text message confirmation code',
                       validators=[DataRequired(message='Text message confirmation code can not be empty'),
                                   Regexp(regex=verify_code,
                                          message='Text message confirmation code must be 5 digits'),
                                   ValidateUserCodes(code_type='sms')])


def email_code():
    verify_code = '^\d{5}$'
    return StringField("Email confirmation code",
                       validators=[DataRequired(message='Email confirmation code can not be empty'),
                                   Regexp(regex=verify_code, message='Email confirmation code must be 5 digits'),
                                   ValidateUserCodes(code_type='email')])


class LoginForm(Form):
    email_address = StringField('Email address', validators=[
        Length(min=5, max=255),
        DataRequired(message='Email cannot be empty'),
        Email(message='Enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Enter your password')
    ])


class RegisterUserForm(Form):
    def __init__(self, existing_email_addresses, *args, **kwargs):
        self.existing_emails = existing_email_addresses
        super(RegisterUserForm, self).__init__(*args, **kwargs)

    name = StringField('Full name',
                       validators=[DataRequired(message='Name can not be empty')])
    email_address = email_address()
    mobile_number = mobile_number()
    password = password()

    def validate_email_address(self, field):
        # Validate email address is unique.
        if self.existing_emails(field.data):
            raise ValidationError('Email address already exists')


class TwoFactorForm(Form):
    def __init__(self, user_codes, *args, **kwargs):
        '''
        Keyword arguments:
        user_codes -- List of user code objects which have the fields
        (code_type, expiry_datetime, code)
        '''
        self.user_codes = user_codes
        super(TwoFactorForm, self).__init__(*args, **kwargs)

    sms_code = sms_code()


class VerifyForm(Form):
    def __init__(self, user_codes, *args, **kwargs):
        '''
        Keyword arguments:
        user_codes -- List of user code objects which have the fields
        (code_type, expiry_datetime, code)
        '''
        self.user_codes = user_codes
        super(VerifyForm, self).__init__(*args, **kwargs)

    sms_code = sms_code()
    email_code = email_code()


class EmailNotReceivedForm(Form):
    email_address = email_address()


class TextNotReceivedForm(Form):
    mobile_number = mobile_number()


class AddServiceForm(Form):
    def __init__(self, service_names, *args, **kwargs):
        self.service_names = service_names
        super(AddServiceForm, self).__init__(*args, **kwargs)

    service_name = StringField(validators=[
        DataRequired(message='Service name can not be empty')])

    def validate_service_name(self, a):
        if self.service_name.data in self.service_names:
            raise ValidationError('Service name already exists')


class ForgotPasswordForm(Form):
    email_address = email_address()

    def __init__(self, q, *args, **kwargs):
        self.query_function = q
        super(ForgotPasswordForm, self).__init__(*args, **kwargs)

    def validate_email_address(self, a):
        if not self.query_function(a.data):
            raise ValidationError('The email address is not recognised. Enter the email address you registered with.')


class NewPasswordForm(Form):
    new_password = password()
