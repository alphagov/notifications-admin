import re
import csv
from io import StringIO, BytesIO
from os import path
from functools import wraps
import unicodedata

from flask import (
    abort,
    current_app,
    redirect,
    request,
    session,
    url_for
)
from flask_login import current_user

from wand.image import Image

from notifications_utils.template import (
    SMSPreviewTemplate,
    EmailPreviewTemplate,
    LetterPDFLinkTemplate,
    LetterPreviewTemplate,
)

import pyexcel
import pyexcel.ext.io
import pyexcel.ext.xls
import pyexcel.ext.xlsx
import pyexcel.ext.ods3


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
                    permissions=permissions,
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

    csvfile = StringIO()
    csvwriter = csv.DictWriter(
        csvfile,
        fieldnames=['Row number', 'Recipient', 'Template', 'Type', 'Job', 'Status', 'Time']
    )

    def read_current_row():
        csvfile.seek(0)
        line = csvfile.read()
        return line

    def clear_file_buffer():
        csvfile.seek(0)
        csvfile.truncate()

    # Initiate download quicker by returning the headers first
    csvwriter.writeheader()
    line = read_current_row()
    clear_file_buffer()
    yield line

    # get_notifications_for_service is always paginated by the api, so set a page param if not specified
    if 'page' not in kwargs:
        kwargs['page'] = 1

    while kwargs['page']:
        notifications_resp = notification_api_client.get_notifications_for_service(**kwargs)
        notifications_list = notifications_resp['notifications']
        for x in notifications_list:
            csvwriter.writerow(format_notification_for_csv(x))

            line = read_current_row()
            clear_file_buffer()
            yield line

        if notifications_resp['links'].get('next'):
            kwargs['page'] += 1
        else:
            return


def format_notification_for_csv(notification):
    from app import format_datetime_24h, format_notification_status
    #  row_number can be 0 so we need to check for it
    row_num = notification.get('job_row_number')
    if row_num is not None and row_num >= 0:
        row_num += 1
    else:
        row_num = ''

    return {
        'Row number': row_num,
        'Recipient': notification['to'],
        'Template': notification['template']['name'],
        'Type': notification['template']['template_type'],
        'Job': notification['job']['original_file_name'] if notification['job'] else '',
        'Status': format_notification_status(notification['status'], notification['template']['template_type']),
        'Time': format_datetime_24h(notification['created_at'])
    }


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
    def from_file(cls, file_content, filename=''):
        extension = cls.get_extension(filename)

        if extension == 'csv':
            return cls(Spreadsheet.normalise_newlines(file_content), filename)

        if extension == 'tsv':
            file_content = StringIO(Spreadsheet.normalise_newlines(file_content))

        return cls.from_rows(pyexcel.get_sheet(
            file_type=extension,
            file_content=file_content.read()
        ).to_array(), filename)


def get_help_argument():
    return request.args.get('help') if request.args.get('help') in ('1', '2', '3') else None


def is_gov_user(email_address):
    valid_domains = current_app.config['EMAIL_DOMAIN_REGEXES']
    email_regex = (r"[\.|@]({})$".format("|".join(valid_domains)))
    return bool(re.search(email_regex, email_address.lower()))


def get_template(
    template,
    service,
    show_recipient=False,
    expand_emails=False,
    letter_preview_url=None,
):
    if 'email' == template['template_type']:
        return EmailPreviewTemplate(
            template,
            from_name=service['name'],
            from_address='{}@notifications.service.gov.uk'.format(service['email_from']),
            expanded=expand_emails,
            show_recipient=show_recipient
        )
    if 'sms' == template['template_type']:
        return SMSPreviewTemplate(
            template,
            prefix=service['name'],
            sender=service['sms_sender'],
            show_recipient=show_recipient
        )
    if 'letter' == template['template_type']:
        if letter_preview_url:
            return LetterPDFLinkTemplate(
                template,
                preview_url=letter_preview_url,
            )
        else:
            return LetterPreviewTemplate(
                template
            )


def png_from_pdf(pdf_endpoint):
    output = BytesIO()
    with Image(
        blob=pdf_endpoint.get_data(),
        resolution=96,
    ) as image:
        with image.convert('png') as converted:
            converted.save(file=output)
    output.seek(0)
    return dict(
        filename_or_fp=output,
        mimetype='image/png',
    )
