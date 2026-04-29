import math
import mimetypes
import uuid
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from flask import abort, current_app, url_for
from notifications_utils.base64_uuid import uuid_to_base64
from notifications_utils.s3 import s3download
from notifications_utils.serialised_model import SerialisedModelCollection
from notifications_utils.template import Template

from app.models import JSONModel
from app.s3_client.s3_template_email_file_upload_client import (
    download_template_email_file_from_s3,
    upload_template_email_file_to_s3,
)


def _get_file_location(file_id: uuid, service_id: uuid) -> str:
    return f"{service_id}/{file_id}"


class TemplateEmailFile(JSONModel):
    id: Any
    service_id: Any
    template: Any
    filename: str
    link_text: str
    retention_period: int
    validate_users_email: bool
    pending: bool

    __sort_attribute__ = "position_in_template"

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
        return file_id

    def copy_file(
        self,
        destination_template_id,
        destination_service_id,
        validate_users_email,
        retention_period,
        link_text,
    ):
        from app import current_user, template_email_file_client

        destination_file_id = str(uuid.uuid4())
        source_file_location = _get_file_location(self.id, self.service_id)
        destination_file_bytes = download_template_email_file_from_s3(file_location=source_file_location).read()
        destination_file_location = _get_file_location(file_id=destination_file_id, service_id=destination_service_id)
        upload_template_email_file_to_s3(data=destination_file_bytes, file_location=destination_file_location)

        template_email_file_client.create_file(
            file_id=destination_file_id,
            service_id=destination_service_id,
            template_id=destination_template_id,
            filename=self.filename,
            created_by_id=current_user.id,
        )

        return template_email_file_client.update_file(
            service_id=destination_service_id,
            template_id=destination_template_id,
            file_id=destination_file_id,
            pending=False,
            link_text=link_text,
            retention_period=retention_period,
            validate_users_email=validate_users_email,
        )

    def update(self, **kwargs):
        from app import template_email_file_client

        data = {
            "link_text": self.link_text or "",
            "retention_period": self.retention_period,
            "validate_users_email": self.validate_users_email,
            "pending": self.pending,
        } | kwargs

        return template_email_file_client.update_file(
            service_id=self.service_id, template_id=self.template.id, file_id=self.id, **data
        )

    @classmethod
    def get_by_id(cls, template_email_file_id: str, service_id: str, template: Template):
        from app import template_email_file_client

        template_email_file = template_email_file_client.get_file_by_id(template_email_file_id, service_id, template.id)
        template_email_file["data"]["service_id"] = service_id
        template_email_file["data"]["template"] = template
        return cls(template_email_file.get("data"))

    @property
    def link_as_markdown(self):
        link = url_for(
            "main.document_download_landing",
            service_id=self.service_id,
            document_id=self.id,
            key=uuid_to_base64(self.template.id),
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

    @property
    def position_in_template(self):
        with suppress(KeyError):
            return self.template.all_placeholders.index(self.filename)
        return math.inf


class TemplateEmailFiles(SerialisedModelCollection):
    model = TemplateEmailFile

    def __init__(self, template):
        from app import current_service

        self.service_id = current_service.id
        self.template = template

        super().__init__(template._template.get("email_files", []))

    def __getitem__(self, index):
        return self.model(self.items[index] | {"service_id": self.service_id, "template": self.template})

    @property
    def as_personalisation(self):
        return {template_email_file.filename: template_email_file.link_as_markdown for template_email_file in self}

    def by_id(self, template_email_file_id):
        for row in self:
            if row.id == str(template_email_file_id):
                return row
        abort(404)
