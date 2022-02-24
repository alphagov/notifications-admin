import urllib
import uuid

import boto3
import botocore
import pytest
from flask import current_app
from moto import mock_s3

from app.s3_client.s3_letter_upload_client import (
    LetterMetadata,
    LetterNotFoundError,
    backup_original_letter_to_s3,
    get_letter_metadata,
    upload_letter_to_s3,
)


def test_backup_original_letter_to_s3(mocker, notify_admin):
    s3_mock = mocker.patch('app.s3_client.s3_letter_upload_client.utils_s3upload')
    upload_id = uuid.uuid4()

    backup_original_letter_to_s3(
        'pdf_data',
        upload_id=upload_id,
    )

    s3_mock.assert_called_once_with(
        bucket_name=current_app.config['PRECOMPILED_ORIGINALS_BACKUP_LETTERS'],
        file_location=f'{str(upload_id)}.pdf',
        filedata='pdf_data',
        region=current_app.config['AWS_REGION']
    )


def test_upload_letter_to_s3(mocker):
    s3_mock = mocker.patch('app.s3_client.s3_letter_upload_client.utils_s3upload')

    recipient = 'Bugs Bunny\n123 Big Hole\nLooney Town'
    upload_letter_to_s3(
        'pdf_data',
        file_location='service_id/upload_id.pdf',
        status='valid',
        page_count=3,
        filename='my_doc',
        recipient=recipient
    )

    s3_mock.assert_called_once_with(
        bucket_name=current_app.config['TRANSIENT_UPLOADED_LETTERS'],
        file_location='service_id/upload_id.pdf',
        filedata='pdf_data',
        metadata={'status': 'valid', 'page_count': '3', 'filename': 'my_doc',
                  'recipient': urllib.parse.quote(recipient)},
        region=current_app.config['AWS_REGION']
    )


def test_upload_letter_to_s3_with_message_and_invalid_pages(mocker):
    s3_mock = mocker.patch('app.s3_client.s3_letter_upload_client.utils_s3upload')

    upload_letter_to_s3(
        'pdf_data',
        file_location='service_id/upload_id.pdf',
        status='invalid',
        page_count=3,
        filename='my_doc',
        message='This file failed',
        invalid_pages=[1, 2, 5])

    s3_mock.assert_called_once_with(
        bucket_name=current_app.config['TRANSIENT_UPLOADED_LETTERS'],
        file_location='service_id/upload_id.pdf',
        filedata='pdf_data',
        metadata={
            'status': 'invalid',
            'page_count': '3',
            'filename': 'my_doc',
            'message': 'This file failed',
            'invalid_pages': '[1, 2, 5]'
        },
        region=current_app.config['AWS_REGION']
    )


def test_lettermetadata_gets_non_special_keys():
    metadata = LetterMetadata({"key": "value", "not_key_to_decode": "%C2%A3"})
    assert metadata.get("key") == "value"
    assert metadata.get("other_key") is None
    assert metadata.get("other_key", "default") == "default"
    assert metadata.get("not_key_to_decode") == "%C2%A3"


def test_lettermetadata_unquotes_special_keys():
    metadata = LetterMetadata({"filename": "%C2%A3hello", "recipient": "%C2%A3hi"})
    assert metadata.get("filename") == "£hello"
    assert metadata.get("recipient") == "£hi"


@mock_s3
@pytest.mark.parametrize('will_raise_custom_error,expected_exception', [
    (True, LetterNotFoundError),
    (False, botocore.exceptions.ClientError)
])
def test_get_letter_s3_object_raises_custom_error(
    will_raise_custom_error,
    expected_exception
):
    bucket_name = current_app.config['TRANSIENT_UPLOADED_LETTERS']
    s3 = boto3.client('s3', region_name='eu-west-1')

    # bucket not existing will trigger some other error
    if will_raise_custom_error:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'}
        )

    with pytest.raises(expected_exception):
        get_letter_metadata('service', 'file')
