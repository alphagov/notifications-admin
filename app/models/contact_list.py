from flask import abort, current_app
from notifications_utils.formatters import strip_whitespace

from app.models import JSONModel
from app.notify_client.contact_list_api_client import contact_list_api_client
from app.s3_client.s3_csv_client import (
    get_csv_metadata,
    s3download,
    s3upload,
    set_metadata_on_csv_upload,
)


class ContactList(JSONModel):

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

    @staticmethod
    def copy_to_uploads(service_id, upload_id):
        contents = ContactList.download(service_id, upload_id)
        metadata = ContactList.get_metadata(service_id, upload_id)
        new_upload_id = s3upload(
            service_id,
            contents,
            current_app.config['AWS_REGION'],
        )
        set_metadata_on_csv_upload(
            service_id,
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
