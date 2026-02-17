import uuid
from typing import Any

from flask import abort, current_app, url_for
from notifications_utils.base64_uuid import uuid_to_base64
from notifications_utils.serialised_model import SerialisedModelCollection

from app.models import JSONModel
from app.s3_client.s3_preview_document_download_client import preview_document_download_client
from app.s3_client.s3_template_email_file_upload_client import upload_template_email_file_to_s3
from app.utils import bytes_to_pretty_file_size


def _get_file_location(file_id: uuid, service_id: uuid) -> str:
    return f"{service_id}/{file_id}"


class TemplateEmailFile(JSONModel):
    id: Any
    service_id: Any
    template_id: Any
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

    def update(self, **kwargs):
        from app import template_email_file_client

        data = {
            "link_text": self.link_text or "",
            "retention_period": self.retention_period,
            "validate_users_email": self.validate_users_email,
        } | kwargs

        return template_email_file_client.update_file(
            service_id=self.service_id, template_id=self.template_id, file_id=self.id, **data
        )

    @property
    def link_as_markdown(self):
        link = url_for(
            "main.document_download_index",
            service_id=self.service_id,
            document_id=self.id,
            key=uuid_to_base64(self.template_id),
            _external=True,
        )
        if self.link_text:
            return f"[{self.link_text}]({link})"
        return link

    @property
    def size(self):
        metadata = preview_document_download_client.get_file_metadata_from_s3(
            current_app.config["S3_BUCKET_TEMPLATE_EMAIL_FILES"],
            f"{self.service_id}/{self.id}",
        )
        return bytes_to_pretty_file_size(metadata.get("ContentLength", 0))

    @property
    def extension(self):
        return self.filename.split(".")[-1]

    @property
    def mimetype(self):
        return current_app.config["FILE_EXTENSIONS_TO_MIMETYPES"][self.extension]

    @property
    def file_type(self):
        return current_app.config["FILE_EXTENSION_TO_PRETTY_FILE_TYPE"][self.extension]

    def get_file_content_for_download(self):
        filename = f"{self.service_id}/{self.id}"
        bucket_name = current_app.config["S3_BUCKET_TEMPLATE_EMAIL_FILES"]
        file_object_body = preview_document_download_client.get_file_object_body_from_s3(bucket_name, filename)
        file_data = file_object_body.read()
        return file_data


class TemplateEmailFiles(SerialisedModelCollection):
    model = TemplateEmailFile

    def __init__(self, items, *, template_id):
        from app import current_service

        self.service_id = current_service.id
        self.template_id = template_id
        super().__init__(items)

    def __getitem__(self, index):
        return self.model(self.items[index] | {"service_id": self.service_id, "template_id": self.template_id})

    @property
    def as_personalisation(self):
        return {template_email_file.filename: template_email_file.link_as_markdown for template_email_file in self}

    def by_id(self, template_email_file_id):
        for row in self:
            if row.id == str(template_email_file_id):
                return row
        abort(404)
