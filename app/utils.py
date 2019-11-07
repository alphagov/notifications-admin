import csv
import os
import re
import unicodedata
from datetime import datetime, time, timedelta, timezone
from functools import wraps
from io import BytesIO, StringIO
from itertools import chain
from numbers import Number
from os import path
from urllib.parse import urlparse

import ago
import dateutil
import pyexcel
import pyexcel_xlsx
from dateutil import parser
from flask import abort, current_app, redirect, request, session, url_for
from flask_login import current_user, login_required
from notifications_utils.field import Field
from notifications_utils.formatters import (
    make_quotes_smart,
    unescaped_formatted_list,
)
from notifications_utils.letter_timings import letter_can_be_cancelled
from notifications_utils.recipients import RecipientCSV
from notifications_utils.take import Take
from notifications_utils.template import (
    EmailPreviewTemplate,
    LetterImageTemplate,
    LetterPreviewTemplate,
    SMSPreviewTemplate,
)
from notifications_utils.timezones import (
    convert_utc_to_bst,
    utc_string_to_aware_gmt_datetime,
)
from orderedset._orderedset import OrderedSet
from werkzeug.datastructures import MultiDict
from werkzeug.routing import RequestRedirect

from app.notify_client.organisations_api_client import organisations_client

SENDING_STATUSES = ['created', 'pending', 'sending', 'pending-virus-check']
DELIVERED_STATUSES = ['delivered', 'sent', 'returned-letter']
FAILURE_STATUSES = ['failed', 'temporary-failure', 'permanent-failure',
                    'technical-failure', 'virus-scan-failed', 'validation-failed']
REQUESTED_STATUSES = SENDING_STATUSES + DELIVERED_STATUSES + FAILURE_STATUSES


with open('{}/email_domains.txt'.format(
    os.path.dirname(os.path.realpath(__file__))
)) as email_domains:
    GOVERNMENT_EMAIL_DOMAIN_NAMES = [line.strip() for line in email_domains]


user_is_logged_in = login_required


def user_has_permissions(*permissions, **permission_kwargs):
    def wrap(func):
        @wraps(func)
        def wrap_func(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            if not current_user.has_permissions(*permissions, **permission_kwargs):
                abort(403)
            return func(*args, **kwargs)
        return wrap_func
    return wrap


def user_is_gov_user(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        if not current_user.is_gov_user:
            abort(403)
        return f(*args, **kwargs)
    return wrapped


def user_is_platform_admin(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        if not current_user.platform_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapped


def redirect_to_sign_in(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'user_details' not in session:
            return redirect(url_for('main.sign_in'))
        else:
            return f(*args, **kwargs)
    return wrapped


def get_errors_for_csv(recipients, template_type):

    errors = []

    if any(recipients.rows_with_bad_recipients):
        number_of_bad_recipients = len(list(recipients.rows_with_bad_recipients))
        if 'sms' == template_type:
            if 1 == number_of_bad_recipients:
                errors.append("fix 1 phone number")
            else:
                errors.append("fix {} phone numbers".format(number_of_bad_recipients))
        elif 'email' == template_type:
            if 1 == number_of_bad_recipients:
                errors.append("fix 1 email address")
            else:
                errors.append("fix {} email addresses".format(number_of_bad_recipients))
        elif 'letter' == template_type:
            if 1 == number_of_bad_recipients:
                errors.append("fix 1 address")
            else:
                errors.append("fix {} addresses".format(number_of_bad_recipients))

    if any(recipients.rows_with_missing_data):
        number_of_rows_with_missing_data = len(list(recipients.rows_with_missing_data))
        if 1 == number_of_rows_with_missing_data:
            errors.append("enter missing data in 1 row")
        else:
            errors.append("enter missing data in {} rows".format(number_of_rows_with_missing_data))

    return errors


def generate_notifications_csv(**kwargs):
    from app import notification_api_client
    from app.s3_client.s3_csv_client import s3download
    if 'page' not in kwargs:
        kwargs['page'] = 1

    if kwargs.get('job_id'):
        original_file_contents = s3download(kwargs['service_id'], kwargs['job_id'])
        original_upload = RecipientCSV(
            original_file_contents,
            template_type=kwargs['template_type'],
        )
        original_column_headers = original_upload.column_headers
        fieldnames = ['Row number'] + original_column_headers + ['Template', 'Type', 'Job', 'Status', 'Time']
    else:
        fieldnames = ['Recipient', 'Template', 'Type', 'Sent by', 'Sent by email', 'Job', 'Status', 'Time']

    yield ','.join(fieldnames) + '\n'

    while kwargs['page']:
        notifications_resp = notification_api_client.get_notifications_for_service(**kwargs)
        for notification in notifications_resp['notifications']:
            if kwargs.get('job_id'):
                values = [
                    notification['row_number'],
                ] + [
                    original_upload[notification['row_number'] - 1].get(header).data
                    for header in original_column_headers
                ] + [
                    notification['template_name'],
                    notification['template_type'],
                    notification['job_name'],
                    notification['status'],
                    notification['created_at'],
                ]
            else:
                values = [
                    notification['recipient'],
                    notification['template_name'],
                    notification['template_type'],
                    notification['created_by_name'] or '',
                    notification['created_by_email_address'] or '',
                    notification['job_name'] or '',
                    notification['status'],
                    notification['created_at']
                ]
            yield Spreadsheet.from_rows([map(str, values)]).as_csv_data

        if notifications_resp['links'].get('next'):
            kwargs['page'] += 1
        else:
            return
    raise Exception("Should never reach here")


def get_page_from_request():
    if 'page' in request.args:
        try:
            return int(request.args['page'])
        except ValueError:
            return None
    else:
        return 1


def generate_previous_dict(view, service_id, page, url_args=None):
    return generate_previous_next_dict(view, service_id, page - 1, 'Previous page', url_args or {})


def generate_next_dict(view, service_id, page, url_args=None):
    return generate_previous_next_dict(view, service_id, page + 1, 'Next page', url_args or {})


def generate_previous_next_dict(view, service_id, page, title, url_args):
    return {
        'url': url_for(view, service_id=service_id, page=page, **url_args),
        'title': title,
        'label': 'page {}'.format(page)
    }


def email_safe(string, whitespace='.'):
    # strips accents, diacritics etc
    string = ''.join(c for c in unicodedata.normalize('NFD', string) if unicodedata.category(c) != 'Mn')
    string = ''.join(
        word.lower() if word.isalnum() or word == whitespace else ''
        for word in re.sub(r'\s+', whitespace, string.strip())
    )
    string = re.sub(r'\.{2,}', '.', string)
    return string.strip('.')


def id_safe(string):
    return email_safe(string, whitespace='-')


class Spreadsheet():

    allowed_file_extensions = ['csv', 'xlsx', 'xls', 'ods', 'xlsm', 'tsv']

    def __init__(self, csv_data=None, rows=None, filename=''):

        self.filename = filename

        if csv_data and rows:
            raise TypeError('Spreadsheet must be created from either rows or CSV data')

        self._csv_data = csv_data or ''
        self._rows = rows or []

    @property
    def as_dict(self):
        return {
            'file_name': self.filename,
            'data': self.as_csv_data
        }

    @property
    def as_csv_data(self):
        if not self._csv_data:
            with StringIO() as converted:
                output = csv.writer(converted)
                for row in self._rows:
                    output.writerow(row)
                self._csv_data = converted.getvalue()
        return self._csv_data

    @classmethod
    def can_handle(cls, filename):
        return cls.get_extension(filename) in cls.allowed_file_extensions

    @staticmethod
    def get_extension(filename):
        return path.splitext(filename)[1].lower().lstrip('.')

    @staticmethod
    def normalise_newlines(file_content):
        return '\r\n'.join(file_content.read().decode('utf-8').splitlines())

    @classmethod
    def from_rows(cls, rows, filename=''):
        return cls(rows=rows, filename=filename)

    @classmethod
    def from_dict(cls, dictionary, filename=''):
        return cls.from_rows(
            zip(
                *sorted(dictionary.items(), key=lambda pair: pair[0])
            ),
            filename=filename,
        )

    @classmethod
    def from_file(cls, file_content, filename=''):
        extension = cls.get_extension(filename)

        if extension == 'csv':
            return cls(csv_data=Spreadsheet.normalise_newlines(file_content), filename=filename)

        if extension == 'tsv':
            file_content = StringIO(
                Spreadsheet.normalise_newlines(file_content))

        instance = cls.from_rows(
            pyexcel.iget_array(
                file_type=extension,
                file_stream=file_content),
            filename)
        pyexcel.free_resources()
        return instance

    @property
    def as_rows(self):
        if not self._rows:
            self._rows = list(csv.reader(
                StringIO(self._csv_data),
                quoting=csv.QUOTE_MINIMAL,
                skipinitialspace=True,
            ))
        return self._rows

    @property
    def as_excel_file(self):
        io = BytesIO()
        pyexcel_xlsx.save_data(io, {'Sheet 1': self.as_rows})
        return io.getvalue()


def get_help_argument():
    return request.args.get('help') if request.args.get('help') in ('1', '2', '3') else None


def email_address_ends_with(email_address, known_domains):
    return any(
        email_address.lower().endswith((
            "@{}".format(known),
            ".{}".format(known),
        ))
        for known in known_domains
    )


def is_gov_user(email_address):
    return email_address_ends_with(
        email_address, GOVERNMENT_EMAIL_DOMAIN_NAMES
    ) or email_address_ends_with(
        email_address, organisations_client.get_domains()
    )


def get_template(
    template,
    service,
    show_recipient=False,
    letter_preview_url=None,
    page_count=1,
    redact_missing_personalisation=False,
    email_reply_to=None,
    sms_sender=None,
):
    if 'email' == template['template_type']:
        return EmailPreviewTemplate(
            template,
            from_name=service.name,
            from_address='{}@notifications.service.gov.uk'.format(service.email_from),
            show_recipient=show_recipient,
            redact_missing_personalisation=redact_missing_personalisation,
            reply_to=email_reply_to,
        )
    if 'sms' == template['template_type']:
        return SMSPreviewTemplate(
            template,
            prefix=service.name,
            show_prefix=service.prefix_sms,
            sender=sms_sender,
            show_sender=bool(sms_sender),
            show_recipient=show_recipient,
            redact_missing_personalisation=redact_missing_personalisation,
        )
    if 'letter' == template['template_type']:
        if letter_preview_url:
            return LetterImageTemplate(
                template,
                image_url=letter_preview_url,
                page_count=int(page_count),
                contact_block=template['reply_to_text'],
                postage=template['postage'],
            )
        else:
            return LetterPreviewTemplate(
                template,
                contact_block=template['reply_to_text'],
                admin_base_url=current_app.config['ADMIN_BASE_URL'],
                redact_missing_personalisation=redact_missing_personalisation,
            )


def get_current_financial_year():
    now = datetime.utcnow()
    current_month = int(now.strftime('%-m'))
    current_year = int(now.strftime('%Y'))
    return current_year if current_month > 3 else current_year - 1


def get_time_left(created_at, service_data_retention_days=7):
    return ago.human(
        (
            datetime.now(timezone.utc)
        ) - (
            dateutil.parser.parse(created_at).replace(hour=0, minute=0, second=0) + timedelta(
                days=service_data_retention_days + 1
            )
        ),
        future_tense='Data available for {}',
        past_tense='Data no longer available',  # No-one should ever see this
        precision=1
    )


def email_or_sms_not_enabled(template_type, permissions):
    return (template_type in ['email', 'sms']) and (template_type not in permissions)


def get_logo_cdn_domain():
    parsed_uri = urlparse(current_app.config['ADMIN_BASE_URL'])

    if parsed_uri.netloc.startswith('localhost'):
        return 'static-logos.notify.tools'

    subdomain = parsed_uri.hostname.split('.')[0]
    domain = parsed_uri.netloc[len(subdomain + '.'):]

    return "static-logos.{}".format(domain)


def parse_filter_args(filter_dict):
    if not isinstance(filter_dict, MultiDict):
        filter_dict = MultiDict(filter_dict)

    return MultiDict(
        (
            key,
            (','.join(filter_dict.getlist(key))).split(',')
        )
        for key in filter_dict.keys()
        if ''.join(filter_dict.getlist(key))
    )


def set_status_filters(filter_args):
    status_filters = filter_args.get('status', [])
    return list(OrderedSet(chain(
        (status_filters or REQUESTED_STATUSES),
        DELIVERED_STATUSES if 'delivered' in status_filters else [],
        SENDING_STATUSES if 'sending' in status_filters else [],
        FAILURE_STATUSES if 'failed' in status_filters else []
    )))


def unicode_truncate(s, length):
    encoded = s.encode('utf-8')[:length]
    return encoded.decode('utf-8', 'ignore')


def starts_with_initial(name):
    return bool(re.match(r'^.\.', name))


def remove_middle_initial(name):
    return re.sub(r'\s+.\s+', ' ', name)


def remove_digits(name):
    return ''.join(c for c in name if not c.isdigit())


def normalize_spaces(name):
    return ' '.join(name.split())


def guess_name_from_email_address(email_address):

    possible_name = re.split(r'[\@\+]', email_address)[0]

    if '.' not in possible_name or starts_with_initial(possible_name):
        return ''

    return Take(
        possible_name
    ).then(
        str.replace, '.', ' '
    ).then(
        remove_digits
    ).then(
        remove_middle_initial
    ).then(
        str.title
    ).then(
        make_quotes_smart
    ).then(
        normalize_spaces
    )


def should_skip_template_page(template_type):
    return (
        current_user.has_permissions('send_messages')
        and not current_user.has_permissions('manage_templates', 'manage_api_keys')
        and template_type != 'letter'
    )


def get_default_sms_sender(sms_senders):
    return str(next((
        Field(x['sms_sender'], html='escape')
        for x in sms_senders if x['is_default']
    ), "None"))


def printing_today_or_tomorrow():
    now_utc = datetime.utcnow()
    now_bst = convert_utc_to_bst(now_utc)

    if now_bst.time() < time(17, 30):
        return 'today'
    else:
        return 'tomorrow'


def redact_mobile_number(mobile_number, spacing=""):
    indices = [-4, -5, -6, -7]
    redact_character = spacing + "•" + spacing
    mobile_number_list = list(mobile_number.replace(" ", ""))
    for i in indices:
        mobile_number_list[i] = redact_character
    return "".join(mobile_number_list)


def get_letter_printing_statement(status, created_at):
    created_at_dt = parser.parse(created_at).replace(tzinfo=None)
    if letter_can_be_cancelled(status, created_at_dt):
        return 'Printing starts {} at 5:30pm'.format(printing_today_or_tomorrow())
    else:
        printed_datetime = utc_string_to_aware_gmt_datetime(created_at) + timedelta(hours=6, minutes=30)
        if printed_datetime.date() == datetime.now().date():
            return 'Printed today at 5:30pm'
        elif printed_datetime.date() == datetime.now().date() - timedelta(days=1):
            return 'Printed yesterday at 5:30pm'

        printed_date = printed_datetime.strftime('%d %B').lstrip('0')

        return 'Printed on {} at 5:30pm'.format(printed_date)


LETTER_VALIDATION_MESSAGES = {
    'letter-not-a4-portrait-oriented': {
        'title': 'We cannot print your letter',
        'detail': 'Your letter is not A4 portrait size on {invalid_pages} <br>'
                  'Files must meet our <a href="https://docs.notifications.service.gov.uk/documentation/images/'
                  'notify-pdf-letter-spec-v2.4.pdf" target="_blank">letter specification</a>.'
    },
    'content-outside-printable-area': {
        'title': 'We cannot print your letter',
        'detail': 'The content appears outside the printable area on {invalid_pages}.<br>'
                  'Files must meet our <a href="https://docs.notifications.service.gov.uk/documentation/images/'
                  'notify-pdf-letter-spec-v2.4.pdf" target="_blank">letter specification</a>.'
    },
    'letter-too-long': {
        'title': 'Your letter is too long',
        'detail': 'Letters must be 10 pages or less. <br>Your letter is {page_count} pages long.'
    },
    'no-encoded-string': {
        'title': 'Sanitise failed - No encoded string'
    },
    'unable-to-read-the-file': {
        'title': 'There’s a problem with your file',
        'detail': 'Notify cannot read this PDF.<br>Save a new copy of your file and try again.'
    }
}


def get_letter_validation_error(validation_message, invalid_pages=None, page_count=None):
    if validation_message not in LETTER_VALIDATION_MESSAGES:
        return {'title': 'Validation failed'}

    invalid_pages = unescaped_formatted_list(
        invalid_pages or [],
        before_each='',
        after_each='',
        prefix='page',
        prefix_plural='pages'
    )

    return {
        'title': LETTER_VALIDATION_MESSAGES[validation_message]['title'],
        'detail': LETTER_VALIDATION_MESSAGES[validation_message]['detail'].format(
            invalid_pages=invalid_pages,
            page_count=page_count,
        )
    }


class PermanentRedirect(RequestRedirect):
    """
    In Werkzeug 0.15.0 the status code for RequestRedirect changed from 301 to 308.
    308 status codes are not supported when Internet Explorer is used with Windows 7
    and Windows 8.1, so this class keeps the original status code of 301.
    """
    code = 301


def format_thousands(value):
    if isinstance(value, Number):
        return '{:,.0f}'.format(value)
    if value is None:
        return ''
    return value
