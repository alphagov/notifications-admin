import uuid

from app import current_service, current_user, template_email_file_client
from app.models import JSONModel
from app.s3_client.s3_template_email_file_upload_client import upload_template_email_file_to_s3


def _get_file_location(file_id: uuid, service_id: uuid, template_id: uuid) -> str:
    return f"service-{service_id}/template-{template_id}/{file_id}"


class TemplateEmailFile(JSONModel):
    @staticmethod
    def create(*, filename, file_contents, template_id):
        file_id = uuid.uuid4()
        file_bytes = file_contents.read()
        file_location = _get_file_location(file_id, current_service.id, template_id)
        upload_template_email_file_to_s3(data=file_bytes, file_location=file_location)
        template_email_file_client.create_file(file_id, current_service.id, template_id, filename, current_user)
