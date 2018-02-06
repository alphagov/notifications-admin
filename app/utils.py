import re
import csv
from itertools import chain

import pytz
from io import StringIO
from os import path
from functools import wraps
import unicodedata
from urllib.parse import urlparse
from collections import namedtuple
from datetime import datetime, timedelta, timezone

import dateutil
import ago
from flask import (
    abort,
    current_app,
    redirect,
    request,
    session,
    url_for
)
from flask_login import current_user
import pyexcel

from notifications_utils.template import (
    SMSPreviewTemplate,
    EmailPreviewTemplate,
    LetterImageTemplate,
    LetterPreviewTemplate,
)
from orderedset._orderedset import OrderedSet
from werkzeug.datastructures import MultiDict

SENDING_STATUSES = ['created', 'pending', 'sending']
DELIVERED_STATUSES = ['delivered', 'sent']
FAILURE_STATUSES = ['failed', 'temporary-failure', 'permanent-failure', 'technical-failure']
REQUESTED_STATUSES = SENDING_STATUSES + DELIVERED_STATUSES + FAILURE_STATUSES


class BrowsableItem(object):
    """
    Maps for the template browse-list.
    """

    def __init__(self, item, *args, **kwargs):
        self._item = item
        super(BrowsableItem, self).__init__()

    @property
    def title(self):
        pass

    @property
    def link(self):
        pass

    @property
    def hint(self):
        pass

    @property
    def destructive(self):
        pass


def user_has_permissions(*permissions, admin_override=False, any_=False):
    def wrap(func):
        @wraps(func)
        def wrap_func(*args, **kwargs):
            if current_user and current_user.is_authenticated:
                if current_user.has_permissions(
                    *permissions,
                    admin_override=admin_override,
                    any_=any_
                ):
                    return func(*args, **kwargs)
                else:
                    abort(403)
            else:
                abort(401)
        return wrap_func
    return wrap


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

    if recipients.rows_with_bad_recipients:
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

    if recipients.rows_with_missing_data:
        number_of_rows_with_missing_data = len(list(recipients.rows_with_missing_data))
        if 1 == number_of_rows_with_missing_data:
            errors.append("enter missing data in 1 row")
        else:
            errors.append("enter missing data in {} rows".format(number_of_rows_with_missing_data))

    return errors


def generate_notifications_csv(**kwargs):
    from app import notification_api_client
    if 'page' not in kwargs:
        kwargs['page'] = 1

    if kwargs['job_id']:
        fieldnames = ['Row number', 'Recipient', 'Template', 'Type', 'Job', 'Status', 'Time']
    else:
        fieldnames = ['Recipient', 'Template', 'Type', 'Job', 'Status', 'Time']

    yield ','.join(fieldnames) + '\n'

    while kwargs['page']:
        # if job_id then response looks different
        notifications_resp = notification_api_client.get_notifications_for_service(**kwargs)
        notifications = notifications_resp['notifications']
        if kwargs['job_id']:
            for notification in notifications:
                    values = [
                        notification['row_number'],
                        notification['recipient'],
                        notification['template_name'],
                        notification['template_type'],
                        notification['job_name'],
                        notification['status'],
                        notification['created_at']
                    ]
                    line = ','.join(str(i) for i in values) + '\n'
                    yield line
        else:
            # Change here
            for notification in notifications:
                values = [
                    notification['to'],
                    notification['template']['name'],
                    notification['template']['template_type'],
                    notification.get('job_name', None),
                    notification['status'],
                    notification['created_at'],
                    notification['updated_at']
                ]
                line = ','.join(str(i) for i in values) + '\n'
                yield line
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
        GovernmentDomain(email_address)
        return True
    except NotGovernmentDomain:
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


class NotGovernmentDomain(Exception):
    pass


class GovernmentDomain:

    domains = {
        "gov.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "mod.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "mil.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "ddc-mod.org": {
            "sector": None,
            "agreement_signed": False,
        },
        "slc.co.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "gov.scot": {
            "sector": None,
            "agreement_signed": False,
        },
        "parliament.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "nhs.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "nhs.net": {
            "sector": None,
            "agreement_signed": False,
        },
        "police.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "dclgdatamart.co.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "ucds.email": {
            "sector": None,
            "agreement_signed": False,
        },
        "naturalengland.org.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "hmcts.net": {
            "sector": None,
            "agreement_signed": False,
        },
        "scotent.co.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "assembly.wales": {
            "sector": None,
            "agreement_signed": False,
        },
        "cjsm.net": {
            "sector": None,
            "agreement_signed": False,
        },
        "cqc.org.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "bl.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "stfc.ac.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "wmfs.net": {
            "sector": None,
            "agreement_signed": False,
        },
        "bbsrc.ac.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "acas.org.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "gov.wales": {
            "sector": None,
            "agreement_signed": False,
        },
        "biglotteryfund.org.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "marinemanagement.org.uk": {
            "sector": None,
            "agreement_signed": False,
        },
        "britishmuseum.org": {
            "sector": None,
            "agreement_signed": False,
        },
        "derrystrabane.com": {
            "sector": None,
            "agreement_signed": False,
        },
        "highwaysengland.co.uk": {
            "sector": None,
            "agreement_signed": False,
        },
    }

    def __init__(self, email_address_or_domain):

        for domain, attributes in self.domains.items():
            if re.search(
                "[\.|@]({})$".format(domain.replace(".", "\.")),
                email_address_or_domain.lower()
            ):
                return

        raise NotGovernmentDomain()
