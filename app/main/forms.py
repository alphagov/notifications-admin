import pytz
from flask_wtf import Form
from datetime import datetime, timedelta
from notifications_utils.recipients import (
    validate_phone_number,
    InvalidPhoneError
)
from wtforms import (
    validators,
    StringField,
    PasswordField,
    ValidationError,
    TextAreaField,
    FileField,
    BooleanField,
    HiddenField,
    IntegerField,
    RadioField,
    FieldList,
    DateField)
from wtforms.fields.html5 import EmailField, TelField
from wtforms.validators import (DataRequired, Email, Length, Regexp, Optional)

from app.main.validators import (Blacklist, CsvFileValidator, ValidGovEmail, NoCommasInPlaceHolders)


def get_time_value_and_label(future_time):
    return (
        future_time.replace(tzinfo=None).isoformat(),
        '{} at {}'.format(
            get_human_day(future_time.astimezone(pytz.timezone('Europe/London'))),
            get_human_time(future_time.astimezone(pytz.timezone('Europe/London')))
        )
    )


def get_human_time(time):
    return {
        '0': 'midnight',
        '12': 'midday'
    }.get(
        time.strftime('%-H'),
        time.strftime('%-I%p').lower()
    )


def get_human_day(time, prefix_today_with='T'):
    #  Add 1 hour to get ‘midnight today’ instead of ‘midnight tomorrow’
    time = (time - timedelta(hours=1)).strftime('%A')
    if time == datetime.utcnow().strftime('%A'):
        return '{}oday'.format(prefix_today_with)
    if time == (datetime.utcnow() + timedelta(days=1)).strftime('%A'):
        return 'Tomorrow'
    return time


def get_furthest_possible_scheduled_time():
    return (datetime.utcnow() + timedelta(days=4)).replace(hour=0)


def get_next_hours_until(until):
    now = datetime.utcnow()
    hours = int((until - now).total_seconds() / (60 * 60))
    return [
        (now + timedelta(hours=i)).replace(minute=0, second=0).replace(tzinfo=pytz.utc)
        for i in range(1, hours + 1)
    ]


def get_next_days_until(until):
    now = datetime.utcnow()
    days = int((until - now).total_seconds() / (60 * 60 * 24))
    return [
        get_human_day(
            (now + timedelta(days=i)).replace(tzinfo=pytz.utc),
            prefix_today_with='Later t'
        )
        for i in range(0, days + 1)
    ]


def email_address(label='Email address', gov_user=True):
    validators = [
        Length(min=5, max=255),
        DataRequired(message='Can’t be empty'),
        Email(message='Enter a valid email address')
    ]

    if gov_user:
        validators.append(ValidGovEmail())
    return EmailField(label, validators)


class UKMobileNumber(TelField):
    def pre_validate(self, form):
        try:
            validate_phone_number(self.data)
        except InvalidPhoneError as e:
            raise ValidationError(e.message)


def mobile_number():
    return UKMobileNumber('Mobile number',
                          validators=[DataRequired(message='Can’t be empty')])


def password(label='Password'):
    return PasswordField(label,
                         validators=[DataRequired(message='Can’t be empty'),
                                     Length(8, 255, message='Must be at least 8 characters'),
                                     Blacklist(message='Choose a password that’s harder to guess')])


def sms_code():
    verify_code = '^\d{5}$'
    return StringField('Text message code',
                       validators=[DataRequired(message='Can’t be empty'),
                                   Regexp(regex=verify_code,
                                          message='Must be 5 digits')])


def email_code():
    verify_code = '^\d{5}$'
    return StringField("Email code",
                       validators=[DataRequired(message='Can’t be empty'),
                                   Regexp(regex=verify_code, message='Must be 5 digits')])


class LoginForm(Form):
    email_address = StringField('Email address', validators=[
        Length(min=5, max=255),
        DataRequired(message='Can’t be empty'),
        Email(message='Enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Enter your password')
    ])


class RegisterUserForm(Form):
    name = StringField('Full name',
                       validators=[DataRequired(message='Can’t be empty')])
    email_address = email_address()
    mobile_number = mobile_number()
    password = password()


class RegisterUserFromInviteForm(Form):
    name = StringField('Full name',
                       validators=[DataRequired(message='Can’t be empty')])
    mobile_number = mobile_number()
    password = password()
    service = HiddenField('service')
    email_address = HiddenField('email_address')


class PermissionsForm(Form):
    send_messages = BooleanField("Send messages from existing templates")
    manage_service = BooleanField("Modify this service, its team, and its&nbsp;templates")
    manage_api_keys = BooleanField("Create and revoke API keys")


class InviteUserForm(PermissionsForm):
    email_address = email_address(gov_user=False)

    def __init__(self, invalid_email_address, *args, **kwargs):
        super(InviteUserForm, self).__init__(*args, **kwargs)
        self.invalid_email_address = invalid_email_address.lower()

    def validate_email_address(self, field):
        if field.data.lower() == self.invalid_email_address:
            raise ValidationError("You can’t send an invitation to yourself")


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
            DataRequired(message='Can’t be empty')
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
        u'Service name',
        validators=[
            DataRequired(message='Can’t be empty')
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
        validators=[DataRequired(message="Can’t be empty")])

    template_content = TextAreaField(
        u'Message',
        validators=[
            DataRequired(message="Can’t be empty"),
            NoCommasInPlaceHolders()
        ]
    )


class EmailTemplateForm(SMSTemplateForm):
    subject = TextAreaField(
        u'Subject',
        validators=[DataRequired(message="Can’t be empty")])


class LetterTemplateForm(EmailTemplateForm):
    pass


class ForgotPasswordForm(Form):
    email_address = email_address(gov_user=False)


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


class ChooseTimeForm(Form):

    def __init__(self, *args, **kwargs):
        super(ChooseTimeForm, self).__init__(*args, **kwargs)
        self.scheduled_for.choices = [('', 'Now')] + [
            get_time_value_and_label(hour) for hour in get_next_hours_until(
                get_furthest_possible_scheduled_time()
            )
        ]
        self.scheduled_for.categories = get_next_days_until(get_furthest_possible_scheduled_time())

    scheduled_for = RadioField(
        'When should Notify send these messages?',
        default='',
        validators=[
            DataRequired()
        ]
    )


class CreateKeyForm(Form):
    def __init__(self, existing_key_names=[], *args, **kwargs):
        self.existing_key_names = [x.lower() for x in existing_key_names]
        super(CreateKeyForm, self).__init__(*args, **kwargs)

    key_type = RadioField(
        'What should Notify do when you use this key?',
        validators=[
            DataRequired()
        ]
    )

    key_name = StringField(u'Description of key', validators=[
        DataRequired(message='You need to give the key a name')
    ])

    def validate_key_name(self, key_name):
        if key_name.data.lower() in self.existing_key_names:
            raise ValidationError('A key with this name already exists')


class Feedback(Form):
    name = StringField('Name')
    email_address = StringField('Email address')
    feedback = TextAreaField(u'', validators=[DataRequired(message="Can’t be empty")])


class RequestToGoLiveForm(Form):
    mou = RadioField(
        (
            'Has your organisation accepted the GOV.UK&nbsp;Notify data sharing and financial '
            'agreement (Memorandum of Understanding)?'
        ),
        choices=[
            ('yes', 'Yes'),
            ('no', 'No'),
            ('don’t know', 'I don’t know')
        ],
        validators=[DataRequired()]
    )
    channel = RadioField(
        'What kind of messages will you be sending?',
        choices=[
            ('emails', 'Emails'),
            ('text messages', 'Text messages'),
            ('emails and text messages', 'Both')
        ],
        validators=[DataRequired()]
    )
    start_date = StringField(
        'When will you be ready to start sending messages?',
        validators=[DataRequired(message='Can’t be empty')]
    )
    start_volume = StringField(
        'How many messages do you expect to send to start with?',
        validators=[DataRequired(message='Can’t be empty')]
    )
    peak_volume = StringField(
        'Will the number of messages increase and when will that start?',
        validators=[DataRequired(message='Can’t be empty')]
    )
    upload_or_api = RadioField(
        'How are you going to send messages?',
        choices=[
            ('File upload', 'Upload a spreadsheet of recipients'),
            ('API', 'Integrate with the GOV.UK Notify API'),
            ('API and file upload', 'Both')
        ],
        validators=[DataRequired()]
    )


class ProviderForm(Form):
    priority = IntegerField('Priority', [validators.NumberRange(min=1, max=100, message="Must be between 1 and 100")])


class ServiceReplyToEmailFrom(Form):
    email_address = email_address(label='Email reply to address')


class ServiceSmsSender(Form):
    sms_sender = StringField(
        'Text message sender',
        validators=[
            Length(max=11, message="Enter fewer than 11 characters")
        ]
    )

    def validate_sms_sender(form, field):
        import re
        if field.data and not re.match('^[a-zA-Z0-9\s]+$', field.data):
            raise ValidationError('Use letters and numbers only')


class ServiceBrandingOrg(Form):

    def __init__(self, organisations=[], *args, **kwargs):
        self.organisation.choices = organisations
        super(ServiceBrandingOrg, self).__init__(*args, **kwargs)

    branding_type = RadioField(
        'Branding',
        choices=[
            ('govuk', 'GOV.UK only'),
            ('both', 'GOV.UK and organisation'),
            ('org', 'Organisation only')
        ],
        validators=[
            DataRequired()
        ]
    )

    organisation = RadioField(
        'Organisation',
        validators=[
            DataRequired()
        ]
    )


class Whitelist(Form):

    def populate(self, email_addresses, phone_numbers):
        for form_field, existing_whitelist in (
            (self.email_addresses, email_addresses),
            (self.phone_numbers, phone_numbers)
        ):
            for index, value in enumerate(existing_whitelist):
                form_field[index].data = value

    email_addresses = FieldList(
        EmailField(
            '',
            validators=[
                Optional(),
                Email(message='Enter valid email addresses')
            ],
            default=''
        ),
        min_entries=5,
        max_entries=5,
        label="Email addresses"
    )

    phone_numbers = FieldList(
        UKMobileNumber(
            '',
            validators=[
                Optional()
            ],
            default=''
        ),
        min_entries=5,
        max_entries=5,
        label="Mobile numbers"
    )
