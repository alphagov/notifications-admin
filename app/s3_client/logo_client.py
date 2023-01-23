import os
import re
import typing
import uuid

from boto3 import resource
from notifications_utils.s3 import s3upload as utils_s3upload

LOGO_TYPES = typing.Literal["email", "letter"]


class LogoClient:
    TEMPORARY_LOGO_PATHS = {
        "email": "temporary/email/{filename}",
        "letter": "temporary/letter/{filename}",
    }
    PERMANENT_LOGO_PATHS = {
        "email": "email/{filename}",
        "letter": "letters/static/images/letter-template/{filename}",
    }

    def __init__(self):
        # Make sure to call `init_app` to configure the client properly.
        self.region = None
        self.bucket_name = None
        self.client = None

    def init_app(self, application):
        self.region = application.config["AWS_REGION"]
        self.bucket_name = application.config["LOGO_UPLOAD_BUCKET_NAME"]
        self.client = resource("s3")

    def _get_object(self, key_):
        return self.client.Object(self.bucket_name, key_)

    def _slugify(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"\s+", "-", text)
        text = re.sub(r"[^A-Za-z\d\-]", "", text)
        text = re.sub(r"\-{2,}", "-", text)
        text = text.strip("-")
        return text.lower()

    def _get_temporary_logo_key(self, logo_file_name: str, logo_type: LOGO_TYPES) -> str:
        return self.TEMPORARY_LOGO_PATHS[logo_type].format(filename=logo_file_name)

    def _get_permanent_logo_key(
        self, logo_file_name: str, logo_type: LOGO_TYPES, logo_key_extra: typing.Optional[str] = None
    ) -> str:
        """Returns the s3 object key for a permanent logo

        Pass some arbitrary extra context to `logo_key_extra` - this will be normalised and appended to the
        filename.
        """
        if logo_key_extra:
            _file_name, _file_ext = os.path.splitext(logo_file_name)
            logo_key_extra = self._slugify(logo_key_extra)
            logo_file_name = f"{_file_name}-{logo_key_extra}{_file_ext}"

        return self.PERMANENT_LOGO_PATHS[logo_type].format(filename=logo_file_name)

    def save_temporary_logo(
        self, file_data: typing.IO, logo_type: LOGO_TYPES, file_extension: str, content_type: str
    ) -> str:
        """Returns the S3 object key of the uploaded temporary logo.

        args:
            file_data: file-like object
            logo_type: one of: 'email' or 'letter'
            file_extension: eg `.png` - notably should include the full-stop
            content_type: eg 'image/png'

        returns:
            S3 object key (excluding bucket name)
        """
        unique_id = str(uuid.uuid4())
        logo_file_name = f"{unique_id}{file_extension}"
        temporary_logo_key = self._get_temporary_logo_key(logo_file_name=logo_file_name, logo_type=logo_type)
        utils_s3upload(
            filedata=file_data,
            region=self.region,
            bucket_name=self.bucket_name,
            file_location=temporary_logo_key,
            content_type=content_type,
        )
        return temporary_logo_key

    def save_permanent_logo(
        self, temporary_logo_key: str, logo_type: LOGO_TYPES, logo_key_extra: typing.Optional[str] = None
    ) -> str:
        """Takes a temporary logo S3 object key and copies it to an immutable, must-never-be-deleted final location.

        args:
            temporary_logo_key: s3 object key to existing temporary logo
            logo_type: one of: 'email' or 'letter'
            logo_key_extra: some extra context to include in the s3 object key/absolute path. will be normalised.

        returns:
            S3 object key (excluding bucket name)
        """
        logo_key = os.path.basename(temporary_logo_key)

        permanent_logo_key = self._get_permanent_logo_key(
            logo_file_name=logo_key, logo_type=logo_type, logo_key_extra=logo_key_extra
        )

        self._get_object(permanent_logo_key).copy_from(CopySource="{}/{}".format(self.bucket_name, temporary_logo_key))

        return permanent_logo_key


logo_client = LogoClient()
