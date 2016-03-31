from flask_wtf import Form
from utils.recipients import (
    validate_phone_number,
    InvalidPhoneError
)
from wtforms import (
    StringField,
    PasswordField,
    ValidationError,
    TextAreaField,
    FileField,
    BooleanField,
    HiddenField
)
from wtforms.fields.html5 import EmailField, TelField
from wtforms.validators import (DataRequired, Email, Length, Regexp)

from app.main.validators import (Blacklist, CsvFileValidator, ValidEmailDomainRegex)


def email_address(label='Email address'):
    return EmailField(label, validators=[
        Length(min=5, max=255),
        DataRequired(message='Email cannot be empty'),
        Email(message='Enter a valid email address'),
        ValidEmailDomainRegex()])


class UKMobileNumber(TelField):

    def pre_validate(self, form):
        try:
            validate_phone_number(self.data)
        except InvalidPhoneError as e:
            raise ValidationError(e.message)


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


class RegisterUserFromInviteForm(Form):
    name = StringField('Full name',
                       validators=[DataRequired(message='Name can not be empty')])
    mobile_number = mobile_number()
    password = password()
    service = HiddenField('service')
    email_address = HiddenField('email_address')


class PermissionsForm(Form):

    send_messages = BooleanField("Send messages from existing templates")
    manage_service = BooleanField("Modify this service, its team, and its&nbsp;templates")
    manage_api_keys = BooleanField("Create and revoke API keys")


class InviteUserForm(PermissionsForm):

    email_address = email_address('Email address')

    def __init__(self, invalid_email_address, *args, **kwargs):
        super(InviteUserForm, self).__init__(*args, **kwargs)
        self.invalid_email_address = invalid_email_address.lower()

    def validate_email_address(self, field):
        if field.data.lower() == self.invalid_email_address:
            raise ValidationError("You can't send an invitation to yourself")


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
            DataRequired(message='Service name can’t be empty')
        ]
    )

    def validate_name(self, a):
        from app.utils import email_safe
        # make sure the email_from will be unique to all services
        if email_safe(a.data) in self._names_func():
            raise ValidationError('This service name is already in use')


class ServiceNameForm(Form):
    def __init__(self, names_func, *args, **kwargs):
        """
        Keyword arguments:
        names_func -- Returns a list of unique service_names already registered
        on the system.
        """
        self._names_func = names_func
        super(ServiceNameForm, self).__init__(*args, **kwargs)

    name = StringField(
        u'New name',
        validators=[
            DataRequired(message='Service name can’t be empty')
        ])

    def validate_name(self, a):
        from app.utils import email_safe
        # make sure the email_from will be unique to all services
        if email_safe(a.data) in self._names_func():
            raise ValidationError('This service name is already in use')


class ConfirmPasswordForm(Form):

    def __init__(self, validate_password_func, *args, **kwargs):
        self.validate_password_func = validate_password_func
        super(ConfirmPasswordForm, self).__init__(*args, **kwargs)

    password = PasswordField(u'Enter password')

    def validate_password(self, field):
        if not self.validate_password_func(field.data):
            raise ValidationError('Invalid password')


class SMSTemplateForm(Form):
    name = StringField(
        u'Template name',
        validators=[DataRequired(message="Template name cannot be empty")])

    template_content = TextAreaField(
        u'Message',
        validators=[DataRequired(message="Template content cannot be empty")])


class EmailTemplateForm(SMSTemplateForm):

    subject = StringField(
        u'Subject',
        validators=[DataRequired(message="Subject cannot be empty")])


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
    file = FileField('Add recipients', validators=[DataRequired(
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
