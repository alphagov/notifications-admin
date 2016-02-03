import re
from flask_wtf import Form

from wtforms import (
    StringField,
    PasswordField,
    ValidationError,
    TextAreaField,
    FileField,
    RadioField
)
from wtforms.validators import DataRequired, Email, Length, Regexp

from app.main.validators import Blacklist, CsvFileValidator

from app.main.utils import (
    validate_phone_number,
    format_phone_number,
    InvalidPhoneError
)


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
        try:
            self.data = validate_phone_number(self.data)
        except InvalidPhoneError as e:
            raise ValidationError(e.message)

    def post_validate(self, form, validation_stopped):

        if len(self.data) != 9:
            return
        # TODO implement in the render field method.
        # API's require no spaces in the number
        # self.data = '+44 7{} {} {}'.format(*re.findall('...', self.data))
        self.data = format_phone_number(self.data)


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
    return StringField('Text message code',
                       validators=[DataRequired(message='Text message confirmation code can not be empty'),
                                   Regexp(regex=verify_code,
                                          message='Text message confirmation code must be 5 digits')])


def email_code():
    verify_code = '^\d{5}$'
    return StringField("Email code",
                       validators=[DataRequired(message='Email confirmation code can not be empty'),
                                   Regexp(regex=verify_code, message='Email confirmation code must be 5 digits')])


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

    name = StringField('Full name',
                       validators=[DataRequired(message='Name can not be empty')])
    email_address = email_address()
    mobile_number = mobile_number()
    password = password()


class TwoFactorForm(Form):
    def __init__(self, validate_code_func, *args, **kwargs):
        '''
        Keyword arguments:
        validate_code_func -- Validates the code with the API.
        '''
        self.validate_code_func = validate_code_func
        super(TwoFactorForm, self).__init__(*args, **kwargs)

    sms_code = sms_code()

    def validate_sms_code(self, field):
        is_valid, reason = self.validate_code_func(field.data)
        if not is_valid:
            raise ValidationError(reason)


class VerifyForm(Form):
    def __init__(self, validate_code_func, *args, **kwargs):
        '''
        Keyword arguments:
        validate_code_func -- Validates the code with the API.
        '''
        self.validate_code_func = validate_code_func
        super(VerifyForm, self).__init__(*args, **kwargs)

    sms_code = sms_code()
    email_code = email_code()

    def _validate_code(self, cde, code_type):
        is_valid, reason = self.validate_code_func(cde, code_type)
        if not is_valid:
            raise ValidationError(reason)

    def validate_email_code(self, field):
        self._validate_code(field.data, 'email')

    def validate_sms_code(self, field):
        self._validate_code(field.data, 'sms')


class EmailNotReceivedForm(Form):
    email_address = email_address()


class TextNotReceivedForm(Form):
    mobile_number = mobile_number()


class AddServiceForm(Form):
    def __init__(self, names_func, *args, **kwargs):
        """
        Keyword arguments:
        names_func -- Returns a list of unique service_names already registered
        on the system.
        """
        self._names_func = names_func
        super(AddServiceForm, self).__init__(*args, **kwargs)

    name = StringField(
        'Service name',
        validators=[
            DataRequired(message='Service name can not be empty')
        ]
    )

    def validate_name(self, a):
        if a.data in self._names_func():
            raise ValidationError('Service name already exists')


class ServiceNameForm(Form):
    name = StringField(u'New name')


class ConfirmPasswordForm(Form):

    def __init__(self, validate_password_func, *args, **kwargs):
        self.validate_password_func = validate_password_func
        super(ConfirmPasswordForm, self).__init__(*args, **kwargs)

    password = PasswordField(u'Enter password')

    def validate_password(self, field):
        if not self.validate_password_func(field.data):
            raise ValidationError('Invalid password')


class TemplateForm(Form):
    name = StringField(
        u'Template name',
        validators=[DataRequired(message="Template name cannot be empty")])
    template_type = RadioField(u'Template type', choices=[('sms', 'SMS')])

    template_content = TextAreaField(
        u'Message',
        validators=[DataRequired(message="Template content cannot be empty")])


class ForgotPasswordForm(Form):
    email_address = email_address()


class NewPasswordForm(Form):
    new_password = password()


class ChangePasswordForm(Form):

    def __init__(self, validate_password_func, *args, **kwargs):
        self.validate_password_func = validate_password_func
        super(ChangePasswordForm, self).__init__(*args, **kwargs)

    old_password = password('Current password')
    new_password = password('New password')

    def validate_old_password(self, field):
        if not self.validate_password_func(field.data):
            raise ValidationError('Invalid password')


class CsvUploadForm(Form):
    file = FileField('Add your recipients by uploading a CSV file', validators=[DataRequired(
                     message='Please pick a file'), CsvFileValidator()])


class ChangeNameForm(Form):
    new_name = StringField(u'Your name')


class ChangeEmailForm(Form):

    def __init__(self, validate_email_func, *args, **kwargs):
        self.validate_email_func = validate_email_func
        super(ChangeEmailForm, self).__init__(*args, **kwargs)

    email_address = email_address()

    def validate_email_address(self, field):
        is_valid = self.validate_email_func(field.data)
        if not is_valid:
            raise ValidationError("The email address is already in use")


class ConfirmEmailForm(Form):

    def __init__(self, validate_code_func, *args, **kwargs):
        self.validate_code_func = validate_code_func
        super(ConfirmEmailForm, self).__init__(*args, **kwargs)

    email_code = email_code()

    def validate_email_code(self, field):
        is_valid, msg = self.validate_code_func(field.data)
        if not is_valid:
            raise ValidationError(msg)


class ChangeMobileNumberForm(Form):
    mobile_number = mobile_number()


class ConfirmMobileNumberForm(Form):

    def __init__(self, validate_code_func, *args, **kwargs):
        self.validate_code_func = validate_code_func
        super(ConfirmMobileNumberForm, self).__init__(*args, **kwargs)

    sms_code = sms_code()

    def validate_sms_code(self, field):
        is_valid, msg = self.validate_code_func(field.data)
        if not is_valid:
            raise ValidationError(msg)


class CreateKeyForm(Form):
    def __init__(self, existing_key_names=[], *args, **kwargs):
        self.existing_key_names = [x.lower() for x in existing_key_names]
        super(CreateKeyForm, self).__init__(*args, **kwargs)

    key_name = StringField(u'Description of key', validators=[
        DataRequired(message='You need to give the key a name')
    ])

    def validate_key_name(self, key_name):
        if key_name.data.lower() in self.existing_key_names:
            raise ValidationError('A key with this name already exists')
