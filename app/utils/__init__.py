from datetime import datetime
from functools import wraps
from itertools import chain
from urllib.parse import urlparse

import pytz
from dateutil import parser
from flask import (
    abort,
    current_app,
    g,
    make_response,
    redirect,
    request,
    session,
    url_for,
)
from flask_login import current_user
from notifications_utils.field import Field
from notifications_utils.recipients import RecipientCSV
from notifications_utils.template import (
    BroadcastPreviewTemplate,
    EmailPreviewTemplate,
    LetterImageTemplate,
    LetterPreviewTemplate,
    SMSPreviewTemplate,
)
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime
from orderedset._orderedset import OrderedSet
from werkzeug.datastructures import MultiDict
from werkzeug.routing import RequestRedirect

from app.models.spreadsheet import Spreadsheet

SENDING_STATUSES = ['created', 'pending', 'sending', 'pending-virus-check']
DELIVERED_STATUSES = ['delivered', 'sent', 'returned-letter']
FAILURE_STATUSES = ['failed', 'temporary-failure', 'permanent-failure',
                    'technical-failure', 'virus-scan-failed', 'validation-failed']
REQUESTED_STATUSES = SENDING_STATUSES + DELIVERED_STATUSES + FAILURE_STATUSES

NOTIFICATION_TYPES = ["sms", "email", "letter", "broadcast"]


def service_has_permission(permission):

    from app import current_service

    def wrap(func):
        @wraps(func)
        def wrap_func(*args, **kwargs):
            if not current_service or not current_service.has_permission(permission):
                abort(403)
            return func(*args, **kwargs)
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

    if any(recipients.rows_with_message_too_long):
        number_of_rows_with_message_too_long = len(list(recipients.rows_with_message_too_long))
        if 1 == number_of_rows_with_message_too_long:
            errors.append("shorten the message in 1 row")
        else:
            errors.append("shorten the messages in {} rows".format(number_of_rows_with_message_too_long))

    if any(recipients.rows_with_empty_message):
        number_of_rows_with_empty_message = len(list(recipients.rows_with_empty_message))
        if 1 == number_of_rows_with_empty_message:
            errors.append("check you have content for the empty message in 1 row")
        else:
            errors.append("check you have content for the empty messages in {} rows".format(
                number_of_rows_with_empty_message
            ))

    return errors


def get_sample_template(template_type):
    if template_type == 'email':
        return EmailPreviewTemplate({'content': 'any', 'subject': '', 'template_type': 'email'})
    if template_type == 'sms':
        return SMSPreviewTemplate({'content': 'any', 'template_type': 'sms'})
    if template_type == 'letter':
        return LetterImageTemplate(
            {'content': 'any', 'subject': '', 'template_type': 'letter'}, postage='second', image_url='x', page_count=1
        )


def generate_notifications_csv(**kwargs):
    from app import notification_api_client
    from app.s3_client.s3_csv_client import s3download
    if 'page' not in kwargs:
        kwargs['page'] = 1

    if kwargs.get('job_id'):
        original_file_contents = s3download(kwargs['service_id'], kwargs['job_id'])
        original_upload = RecipientCSV(
            original_file_contents,
            template=get_sample_template(kwargs['template_type']),
        )
        original_column_headers = original_upload.column_headers
        fieldnames = ['Row number'] + original_column_headers + ['Template', 'Type', 'Job', 'Status', 'Time']
    else:
        fieldnames = ['Recipient', 'Reference', 'Template', 'Type', 'Sent by', 'Sent by email', 'Job', 'Status', 'Time']

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
                    # the recipient for precompiled letters is the full address block
                    notification['recipient'].splitlines()[0].lstrip().rstrip(' ,'),
                    notification['client_reference'],
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


def get_help_argument():
    return request.args.get('help') if request.args.get('help') in ('1', '2', '3') else None


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
    if 'broadcast' == template['template_type']:
        return BroadcastPreviewTemplate(
            template,
        )


def get_current_financial_year():
    now = utc_string_to_aware_gmt_datetime(
        datetime.utcnow()
    )
    current_month = int(now.strftime('%-m'))
    current_year = int(now.strftime('%Y'))
    return current_year if current_month > 3 else current_year - 1


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


class PermanentRedirect(RequestRedirect):
    """
    In Werkzeug 0.15.0 the status code for RequestRedirect changed from 301 to 308.
    308 status codes are not supported when Internet Explorer is used with Windows 7
    and Windows 8.1, so this class keeps the original status code of 301.
    """
    code = 301


def is_less_than_days_ago(date_from_db, number_of_days):
    return (
        datetime.utcnow().astimezone(pytz.utc) - parser.parse(date_from_db)
    ).days < number_of_days


def hide_from_search_engines(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.hide_from_search_engines = True
        response = make_response(f(*args, **kwargs))
        response.headers['X-Robots-Tag'] = 'noindex'
        return response
    return decorated_function


# Function to merge two dict or lists with a JSON-like structure into one.
# JSON-like means they can contain all types JSON can: all the main primitives
# plus nested lists or dictionaries.
# Merge is additive. New values overwrite old and collections are added to.
def merge_jsonlike(source, destination):
    def merge_items(source_item, destination_item):
        if isinstance(source_item, dict) and isinstance(destination_item, dict):
            merge_dicts(source_item, destination_item)
        elif isinstance(source_item, list) and isinstance(destination_item, list):
            merge_lists(source_item, destination_item)
        else:  # primitive value
            return False
        return True

    def merge_lists(source, destination):
        last_src_idx = len(source) - 1
        for idx, item in enumerate(destination):
            if idx <= last_src_idx:
                # assign destination value if can't be merged into source
                if merge_items(source[idx], destination[idx]) is False:
                    source[idx] = destination[idx]
            else:
                source.append(item)

    def merge_dicts(source, destination):
        for key, value in destination.items():
            if key in source:
                # assign destination value if can't be merged into source
                if merge_items(source[key], value) is False:
                    source[key] = value
            else:
                source[key] = value

    merge_items(source, destination)
