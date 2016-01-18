import re
from flask_wtf import Form

from wtforms import (
    StringField,
    PasswordField,
    ValidationError,
    TextAreaField,
    FileField
)
from wtforms.validators import DataRequired, Email, Length, Regexp

from app.main.validators import Blacklist, ValidateUserCodes, CsvFileValidator
from app.main.dao import verify_codes_dao
from app.main.encryption import check_hash


def email_address():
    gov_uk_email \
        = "(^[^@^\\s]+@[^@^\\.^\\s]+(\\.[^@^\\.^\\s]*)*.gov.uk)"
    return StringField('Email address', validators=[
        Length(min=5, max=255),
        DataRequired(message='Email cannot be empty'),
        Email(message='Enter a valid email address'),
        Regexp(regex=gov_uk_email, message='Enter a gov.uk email address')])


class UKMobileNumber(StringField):

    def pre_validate(self, form):

        self.data = self.data.replace('(', '')
        self.data = self.data.replace(')', '')
        self.data = self.data.replace(' ', '')
        self.data = self.data.replace('-', '')

        if self.data.startswith('+'):
            self.data = self.data[1:]

        if not sum(
            self.data.startswith(prefix) for prefix in ['07', '447', '4407', '00447']
        ):
            raise ValidationError('Must be a UK mobile number (eg 07700 900460)')

        for digit in self.data:
            try:
                int(digit)
            except(ValueError):
                raise ValidationError('Must not contain letters or symbols')

        self.data = self.data.split('7', 1)[1]

        if len(self.data) > 9:
            raise ValidationError('Too many digits')

        if len(self.data) < 9:
            raise ValidationError('Not enough digits')

    def post_validate(self, form, validation_stopped):

        if len(self.data) != 9:
            return

        self.data = '+44 7{} {} {}'.format(*re.findall('...', self.data))


def mobile_number():
    return UKMobileNumber('Mobile phone number',
                          validators=[DataRequired(message='Cannot be empty')])


def password(label='Create a password'):
    return PasswordField(label,
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

    service_name = StringField(
        'Service name',
        validators=[
            DataRequired(message='Service name can not be empty')
        ]
    )

    def validate_service_name(self, a):
        if self.service_name.data in self.service_names:
            raise ValidationError('Service name already exists')


class ServiceNameForm(Form):
    service_name = StringField(u'New name')


class ConfirmPasswordForm(Form):
    password = PasswordField(u'Enter password')


class TemplateForm(Form):
    template_name = StringField(u'Template name')
    template_body = TextAreaField(u'Message')


class ForgotPasswordForm(Form):
    email_address = email_address()


class NewPasswordForm(Form):
    new_password = password()


class ChangePasswordForm(Form):
    old_password = password('Current password')
    new_password = password('New password')


class CsvUploadForm(Form):
    file = FileField('File to upload', validators=[DataRequired(
                     message='Please pick a file'), CsvFileValidator()])


class ChangeNameForm(Form):
    new_name = StringField(u'Your name')


class ChangeEmailForm(Form):
    email_address = email_address()


class ConfirmEmailForm(Form):
    email_code = email_code()


class ChangeMobileNumberForm(Form):
    mobile_number = mobile_number()


class ConfirmMobileNumberForm(Form):
    sms_code = sms_code()
