import boto3
from botocore.exceptions import ClientError
from notifications_utils.s3 import S3ObjectNotFound, s3download


class PreviewDocumentDownloadError(Exception):
    def __init__(self, response=None, operation_name=None, message=None):
        self.response = response
        self.operation_name = operation_name
        super().__init__(message)
        self.message = message or "Document download error"

    def __str__(self):
        return self.message


class PreviewDocumentNotFound(PreviewDocumentDownloadError):
    suggested_status_code = 404


class PreviewDocumentDownloadClient:
    def __init__(self):
        self.s3_client = boto3.client("s3")

    def get_file_metadata_from_s3(self, bucket_name, filename):
        try:
            return self.s3_client.head_object(Bucket=bucket_name, Key=filename)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise PreviewDocumentNotFound(
                    e.response,
                    e.operation_name,
                    "Document Metadata not found",
                ) from e
            raise PreviewDocumentDownloadError(e.response, e.operation_name) from e

    @staticmethod
    def get_file_object_body_from_s3(bucket_name, filename):
        try:
            response = s3download(bucket_name, filename)
            return response
        except S3ObjectNotFound as e:
            if e.response["Error"]["Code"] == "404":
                raise PreviewDocumentNotFound(
                    e.response, e.operation_name, "The requested document could not be found"
                ) from e
            raise PreviewDocumentDownloadError(e.response, e.operation_name) from e


preview_document_download_client = PreviewDocumentDownloadClient()
