import mimetypes
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from flask import abort, current_app, url_for
from notifications_utils.base64_uuid import uuid_to_base64
from notifications_utils.s3 import s3download
from notifications_utils.serialised_model import SerialisedModelCollection

from app.models import StrictJSONModel
from app.s3_client.s3_template_email_file_upload_client import upload_template_email_file_to_s3


def _get_file_location(file_id: uuid, service_id: uuid) -> str:
    return f"{service_id}/{file_id}"


class TemplateEmailFile(StrictJSONModel):
    id: Any
    service_id: Any
    template_id: Any
    filename: str
    link_text: str
    retention_period: int
    validate_users_email: bool
    pending: bool

    __sort_attribute__ = "filename"

    @staticmethod
    def create(*, filename, file_contents, template_id, pending=True):
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
        return file_id

    def update(self, **kwargs):
        from app import template_email_file_client

        data = {
            "link_text": self.link_text or "",
            "retention_period": self.retention_period,
            "validate_users_email": self.validate_users_email,
            "pending": self.pending,
        } | kwargs

        return template_email_file_client.update_file(
            service_id=self.service_id, template_id=self.template_id, file_id=self.id, **data
        )

    @classmethod
    def get_by_id(cls, template_email_file_id: str, service_id: str, template_id: str):
        from app import template_email_file_client

        template_email_file = template_email_file_client.get_file_by_id(template_email_file_id, service_id, template_id)
        template_email_file["data"]["service_id"] = service_id
        return cls(template_email_file.get("data"))

    @property
    def link_as_markdown(self):
        link = url_for(
            "main.document_download_landing",
            service_id=self.service_id,
            document_id=self.id,
            key=uuid_to_base64(self.template_id),
            _external=True,
        )
        if self.link_text:
            return f"[{self.link_text}]({link})"
        return link

    @property
    def expiry_date(self):
        return datetime.now(UTC) + timedelta(weeks=self.retention_period)

    @property
    def size(self):
        metadata = boto3.client("s3").head_object(
            Bucket=current_app.config["S3_BUCKET_TEMPLATE_EMAIL_FILES"],
            Key=f"{self.service_id}/{self.id}",
        )
        return metadata.get("ContentLength", 0)

    @property
    def extension(self):
        return self.filename.split(".")[-1]

    @property
    def mimetype(self):
        return mimetypes.types_map[f".{self.extension}"]

    @property
    def file_contents(self):
        return s3download(
            current_app.config["S3_BUCKET_TEMPLATE_EMAIL_FILES"],
            f"{self.service_id}/{self.id}",
        )


class TemplateEmailFiles(SerialisedModelCollection):
    model = TemplateEmailFile

    def __init__(self, template):
        from app import current_service

        self.service_id = current_service.id
        self.template_id = template.id

        email_files = template._template.get("email_files", [])
        super().__init__(email_files)

        position_in_template = (template.index_of_placeholder(email_file.filename) for email_file in self)
        self.items = sorted(email_files, key=lambda _: next(position_in_template))

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
