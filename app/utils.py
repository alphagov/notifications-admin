import re
import csv
from io import StringIO
from os import path
from functools import wraps
from flask import (abort, session, request, redirect, url_for)
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
            from flask_login import current_user
            if current_user and current_user.has_permissions(permissions=permissions,
                                                             admin_override=admin_override, any_=any_):
                return func(*args, **kwargs)
            else:
                abort(403)
        return wrap_func
    return wrap


def redirect_to_sign_in(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        import pdb; pdb.set_trace()
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

    if recipients.rows_with_missing_data:
        number_of_rows_with_missing_data = len(list(recipients.rows_with_missing_data))
        if 1 == number_of_rows_with_missing_data:
            errors.append("enter missing data in 1 row")
        else:
            errors.append("enter missing data in {} rows".format(number_of_rows_with_missing_data))

    return errors


def generate_notifications_csv(json_list):
    from app import format_datetime_24h, format_notification_status
    content = StringIO()
    retval = None
    with content as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['Row number', 'Recipient', 'Template', 'Type', 'Job', 'Status', 'Time'])
        for x in json_list:
            csvwriter.writerow([
                int(x['job_row_number']) + 2 if 'job_row_number' in x and x['job_row_number'] else '',
                x['to'],
                x['template']['name'],
                x['template']['template_type'],
                x['job']['original_file_name'] if x['job'] else '',
                format_notification_status(x['status'], x['template']['template_type']),
                format_datetime_24h(x['created_at'])])
        retval = content.getvalue()
    return retval


def get_page_from_request():
    if 'page' in request.args:
        try:
            return int(request.args['page'])
        except ValueError:
            return None
    else:
        return 1


def generate_previous_next_dict(view, service_id, view_dict, page, title, label):
    if 'page' in view_dict:
        view_dict.pop('page')
    if 'service_id' in view_dict:
        view_dict.pop('service_id')
    return {
        'url': url_for(view, service_id=service_id, page=page, **view_dict),
        'title': title,
        'label': label
    }


def email_safe(string):
    return "".join([
        character.lower() if character.isalnum() or character == "." else "" for character in re.sub("\s+", ".", string.strip())  # noqa
    ])


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
            file_content=file_content.getvalue()
        ).to_array(), filename)


def get_help_argument():
    return request.args.get('help') if request.args.get('help') in ('1', '2', '3') else None
