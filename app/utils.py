import csv
import os
import re
import unicodedata
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from functools import wraps
from io import StringIO
from itertools import chain
from os import path
from urllib.parse import urlparse

import ago
import dateutil
import pyexcel
import pytz
import yaml
from flask import (
    Markup,
    abort,
    current_app,
    redirect,
    request,
    session,
    url_for,
)
from flask_login import current_user
from notifications_utils.recipients import RecipientCSV
from notifications_utils.template import (
    EmailPreviewTemplate,
    LetterImageTemplate,
    LetterPreviewTemplate,
    SMSPreviewTemplate,
)
from orderedset._orderedset import OrderedSet
from werkzeug.datastructures import MultiDict

SENDING_STATUSES = ['created', 'pending', 'sending', 'pending-virus-check']
DELIVERED_STATUSES = ['delivered', 'sent']
FAILURE_STATUSES = ['failed', 'temporary-failure', 'permanent-failure', 'technical-failure', 'virus-scan-failed']
REQUESTED_STATUSES = SENDING_STATUSES + DELIVERED_STATUSES + FAILURE_STATUSES


def user_has_permissions(*permissions, **permission_kwargs):
    def wrap(func):
        @wraps(func)
        def wrap_func(*args, **kwargs):
            if current_user and current_user.is_authenticated:
                if current_user.has_permissions(
                    *permissions,
                    **permission_kwargs
                ):
                    return func(*args, **kwargs)
                else:
                    abort(403)
            else:
                abort(401)
        return wrap_func
    return wrap


def user_is_platform_admin(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
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
    from app.main.s3_client import s3download
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
        fieldnames = ['Recipient', 'Template', 'Type', 'Job', 'Status', 'Time']

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
                    notification['to'],
                    notification['template']['name'],
                    notification['template']['template_type'],
                    notification.get('job_name', None),
                    notification['status'],
                    notification['created_at'],
                    notification['updated_at']
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


class Spreadsheet():

    allowed_file_extensions = ['csv', 'xlsx', 'xls', 'ods', 'xlsm', 'tsv']

    def __init__(self, csv_data, filename=''):
        self.filename = filename
        self.as_csv_data = csv_data
        self.as_dict = {
            'file_name': self.filename,
            'data': self.as_csv_data
        }

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
        with StringIO() as converted:
            output = csv.writer(converted)

            for row in rows:
                output.writerow(row)
            return cls(converted.getvalue(), filename)

    @classmethod
    def from_dict(cls, dictionary, filename=''):
        return cls.from_rows(
            zip(
                *sorted(dictionary.items(), key=lambda pair: pair[0])
            ),
            filename
        )

    @classmethod
    def from_file(cls, file_content, filename=''):
        extension = cls.get_extension(filename)

        if extension == 'csv':
            return cls(Spreadsheet.normalise_newlines(file_content), filename)

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


def get_help_argument():
    return request.args.get('help') if request.args.get('help') in ('1', '2', '3') else None


def is_gov_user(email_address):
    try:
        GovernmentEmailDomain(email_address)
        return True
    except NotGovernmentEmailDomain:
        return False


def get_template(
    template,
    service,
    show_recipient=False,
    expand_emails=False,
    letter_preview_url=None,
    page_count=1,
    redact_missing_personalisation=False,
    email_reply_to=None,
    sms_sender=None,
):
    if 'email' == template['template_type']:
        return EmailPreviewTemplate(
            template,
            from_name=service['name'],
            from_address='{}@notifications.service.gov.uk'.format(service['email_from']),
            expanded=expand_emails,
            show_recipient=show_recipient,
            redact_missing_personalisation=redact_missing_personalisation,
            reply_to=email_reply_to,
        )
    if 'sms' == template['template_type']:
        return SMSPreviewTemplate(
            template,
            prefix=service['name'],
            show_prefix=service['prefix_sms'],
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
                contact_block=template['reply_to_text']
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


def get_time_left(created_at):
    return ago.human(
        (
            datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
        ) - (
            dateutil.parser.parse(created_at) + timedelta(days=8)
        ),
        future_tense='Data available for {}',
        past_tense='Data no longer available',  # No-one should ever see this
        precision=1
    )


def email_or_sms_not_enabled(template_type, permissions):
    return (template_type in ['email', 'sms']) and (template_type not in permissions)


def get_letter_timings(upload_time):

    LetterTimings = namedtuple(
        'LetterTimings',
        'printed_by, is_printed, earliest_delivery, latest_delivery'
    )

    # shift anything after 5pm to the next day
    processing_day = gmt_timezones(upload_time) + timedelta(hours=(7))

    print_day, earliest_delivery, latest_delivery = (
        processing_day + timedelta(days=days)
        for days in {
            'Wednesday': (1, 3, 5),
            'Thursday': (1, 4, 5),
            'Friday': (3, 5, 6),
            'Saturday': (2, 4, 5),
        }.get(processing_day.strftime('%A'), (1, 3, 4))
    )

    printed_by = print_day.astimezone(pytz.timezone('Europe/London')).replace(hour=15, minute=0)
    now = datetime.utcnow().replace(tzinfo=pytz.timezone('Europe/London'))

    return LetterTimings(
        printed_by=printed_by,
        is_printed=(now > printed_by),
        earliest_delivery=earliest_delivery,
        latest_delivery=latest_delivery,
    )


def gmt_timezones(date):
    date = dateutil.parser.parse(date)
    forced_utc = date.replace(tzinfo=pytz.utc)
    return forced_utc.astimezone(pytz.timezone('Europe/London'))


def get_cdn_domain():
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


_dir_path = os.path.dirname(os.path.realpath(__file__))


class AgreementInfo:

    with open('{}/domains.yml'.format(_dir_path)) as domains:
        domains = yaml.safe_load(domains)
        domain_names = sorted(domains.keys(), key=len, reverse=True)

    def __init__(self, email_address_or_domain):

        self._match = next(filter(
            self.get_matching_function(email_address_or_domain),
            self.domain_names,
        ), None)

        (
            self.owner,
            self.crown_status,
            self.agreement_signed
        ) = self._get_info()

    @classmethod
    def from_user(cls, user):
        return cls(user.email_address if user.is_authenticated else '')

    @classmethod
    def from_current_user(cls):
        return cls.from_user(current_user)

    @property
    def as_human_readable(self):
        if self.agreement_signed:
            return 'Yes, on behalf of {}'.format(self.owner)
        elif self.owner:
            return '{} (organisation is {}, {})'.format(
                {
                    False: 'No',
                    None: 'Can’t tell',
                }.get(self.agreement_signed),
                self.owner,
                {
                    True: 'a crown body',
                    False: 'a non-crown body',
                    None: 'crown status unknown',
                }.get(self.crown_status),
            )
        else:
            return 'Can’t tell'

    def as_terms_of_use_paragraph(self, **kwargs):
        return Markup(self._as_terms_of_use_paragraph(**kwargs))

    def _as_terms_of_use_paragraph(self, download_link, contact_link):

        if self.agreement_signed:
            return (
                'Your organisation ({}) has already accepted the '
                'GOV.UK&nbsp;Notify data sharing and financial '
                'agreement.'.format(self.owner)
            )

        if self.crown_status is False:
            return ((
                '{} <a href="{}">Download a copy</a>.'
            ).format(self._acceptance_required, download_link))

        return ((
            '{} <a href="{}">Contact us</a> to get a copy.'
        ).format(self._acceptance_required, contact_link))

    @property
    def _acceptance_required(self):
        return (
            'Your organisation {} must also accept our data sharing '
            'and financial agreement.'.format(
                '({})'.format(self.owner) if self.owner else '',
            )
        )

    @property
    def crown_status_or_404(self):
        if self.crown_status in {None, True}:
            abort(404)
        return self.crown_status

    def as_request_for_agreement(self, with_owner=False):
        if with_owner and self.owner:
            return (
                'Please send me a copy of the GOV.UK Notify data sharing '
                'and financial agreement for {} to sign.'.format(self.owner)
            )
        return (
            'Please send me a copy of the GOV.UK Notify data sharing '
            'and financial agreement.'
        )

    @staticmethod
    def get_matching_function(email_address_or_domain):

        email_address_or_domain = email_address_or_domain.lower()

        def fn(domain):

            return (
                email_address_or_domain == domain
            ) or (
                email_address_or_domain.endswith("@{}".format(domain))
            ) or (
                email_address_or_domain.endswith(".{}".format(domain))
            )

        return fn

    def _get_info(self):

        details = self.domains.get(self._match) or {}

        if isinstance(details, str):
            return AgreementInfo(details)._get_info()

        elif isinstance(details, dict):
            return(
                details.get("owner"),
                details.get("crown"),
                details.get("agreement_signed"),
            )


class NotGovernmentEmailDomain(Exception):
    pass


class GovernmentEmailDomain(AgreementInfo):

    with open('{}/email_domains.yml'.format(_dir_path)) as email_domains:
        domain_names = yaml.safe_load(email_domains)

    def __init__(self, email_address_or_domain):
        try:
            self._match = next(filter(
                self.get_matching_function(email_address_or_domain),
                self.domain_names,
            ))
        except StopIteration:
            raise NotGovernmentEmailDomain()


def unicode_truncate(s, length):
    encoded = s.encode('utf-8')[:length]
    return encoded.decode('utf-8', 'ignore')
