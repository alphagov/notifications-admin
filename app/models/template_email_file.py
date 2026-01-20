import uuid
from typing import Any

from notifications_utils.serialised_model import SerialisedModelCollection

from app.models import JSONModel
from app.s3_client.s3_template_email_file_upload_client import upload_template_email_file_to_s3


def _get_file_location(file_id: uuid, service_id: uuid) -> str:
    return f"{service_id}/{file_id}"


class TemplateEmailFile(JSONModel):
    id: Any
    filename: str
    link_text: str
    retention_period: int
    validate_users_email: bool

    __sort_attribute__ = "filename"

    @staticmethod
    def create(*, filename, file_contents, template_id):
        from app import current_service, current_user, template_email_file_client

        file_id = uuid.uuid4()
        file_bytes = file_contents.read()
        file_location = _get_file_location(file_id, current_service.id)
        upload_template_email_file_to_s3(data=file_bytes, file_location=file_location)
        template_email_file_client.create_file(
            file_id=file_id,
            service_id=current_service.id,
            template_id=template_id,
            filename=filename,
            created_by_id=current_user.id,
        )

    @property
    def link_as_markdown(self):
        if hasattr(self, "link_text") and self.link_text is not None:
            return f"[{self.link_text}](https://example.com/)"
        return f"[{self.filename}](https://example.com/)"


class TemplateEmailFiles(SerialisedModelCollection):
    model = TemplateEmailFile

    @property
    def as_personalisation(self):
        return {template_email_file.filename: template_email_file.link_as_markdown for template_email_file in self}
