from flask import abort

from app.models import JSONModel
from app.notify_client.contact_list_api_client import contact_list_api_client
from app.s3_client.s3_csv_client import get_csv_metadata


class ContactList(JSONModel):

    @classmethod
    def create(cls, service_id, upload_id):

        metadata = get_csv_metadata(service_id, upload_id)

        if not metadata.get('valid'):
            abort(403)

        return cls(contact_list_api_client.create_contact_list(
            service_id=service_id,
            upload_id=upload_id,
            original_file_name=metadata['original_file_name'],
            row_count=int(metadata['row_count']),
            template_type=metadata['template_type'],
        ))
