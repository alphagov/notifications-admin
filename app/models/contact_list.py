from functools import partial
from os import path

from flask import abort, current_app
from notifications_utils.formatters import strip_whitespace
from notifications_utils.recipients import RecipientCSV
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime
from werkzeug.utils import cached_property

from app.models import JSONModel, ModelList
from app.models.job import PaginatedJobs
from app.notify_client.contact_list_api_client import contact_list_api_client
from app.s3_client.s3_csv_client import (
    get_csv_metadata,
    s3download,
    s3upload,
    set_metadata_on_csv_upload,
)
from app.utils import get_sample_template


class ContactList(JSONModel):

    ALLOWED_PROPERTIES = {
        'id',
        'created_by',
        'service_id',
        'original_file_name',
        'row_count',
        'template_type',
    }

    upload_type = 'contact_list'

    @classmethod
    def from_id(cls, contact_list_id, *, service_id):
        return cls(contact_list_api_client.get_contact_list(
            service_id=service_id,
            contact_list_id=contact_list_id,
        ))

    @staticmethod
    def get_bucket_name():
        return current_app.config['CONTACT_LIST_UPLOAD_BUCKET_NAME']

    @staticmethod
    def upload(service_id, file_dict):
        return s3upload(
            service_id,
            file_dict,
            current_app.config['AWS_REGION'],
            bucket=ContactList.get_bucket_name(),
        )

    @staticmethod
    def download(service_id, upload_id):
        return strip_whitespace(s3download(
            service_id,
            upload_id,
            bucket=ContactList.get_bucket_name(),
        ))

    @staticmethod
    def set_metadata(service_id, upload_id, **kwargs):
        return set_metadata_on_csv_upload(
            service_id,
            upload_id,
            bucket=ContactList.get_bucket_name(),
            **kwargs,
        )

    @staticmethod
    def get_metadata(service_id, upload_id):
        return get_csv_metadata(
            service_id,
            upload_id,
            bucket=ContactList.get_bucket_name(),
        )

    def copy_to_uploads(self):
        metadata = self.get_metadata(self.service_id, self.id)
        new_upload_id = s3upload(
            self.service_id,
            {'data': self.contents},
            current_app.config['AWS_REGION'],
        )
        set_metadata_on_csv_upload(
            self.service_id,
            new_upload_id,
            **metadata,
        )
        return new_upload_id

    @classmethod
    def create(cls, service_id, upload_id):

        metadata = cls.get_metadata(service_id, upload_id)

        if not metadata.get('valid'):
            abort(403)

        return cls(contact_list_api_client.create_contact_list(
            service_id=service_id,
            upload_id=upload_id,
            original_file_name=metadata['original_file_name'],
            row_count=int(metadata['row_count']),
            template_type=metadata['template_type'],
        ))

    def delete(self):
        contact_list_api_client.delete_contact_list(
            service_id=self.service_id,
            contact_list_id=self.id,
        )

    @property
    def created_at(self):
        return utc_string_to_aware_gmt_datetime(self._dict['created_at'])

    @property
    def contents(self):
        return self.download(self.service_id, self.id)

    @cached_property
    def recipients(self):
        return RecipientCSV(
            self.contents,
            template=get_sample_template(self.template_type),
            allow_international_sms=True,
            max_initial_rows_shown=50,
        )

    @property
    def saved_file_name(self):
        file_name, extention = path.splitext(self.original_file_name)
        return f'{file_name}.csv'

    def get_jobs(self, *, page):
        return PaginatedJobs(
            self.service_id,
            contact_list_id=self.id,
            page=page,
        )


class ContactLists(ModelList):

    client_method = contact_list_api_client.get_contact_lists
    model = ContactList
    sort_function = partial(
        sorted,
        key=lambda item: item['created_at'],
        reverse=True,
    )

    def __init__(self, service_id, template_type=None):
        super().__init__(service_id)
        self.items = self.sort_function([
            item for item in self.items
            if template_type in {item['template_type'], None}
        ])


class ContactListsAlphabetical(ContactLists):

    sort_function = partial(
        sorted,
        key=lambda item: item['original_file_name'].lower(),
    )
