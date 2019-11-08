import pytest
from flask import current_app

from app.s3_client.s3_letter_upload_client import (
    format_recipient,
    upload_letter_to_s3,
)


def test_upload_letter_to_s3(mocker):
    s3_mock = mocker.patch('app.s3_client.s3_letter_upload_client.utils_s3upload')

    upload_letter_to_s3(
        'pdf_data',
        file_location='service_id/upload_id.pdf',
        status='valid',
        page_count=3,
        filename='my_doc')

    s3_mock.assert_called_once_with(
        bucket_name=current_app.config['TRANSIENT_UPLOADED_LETTERS'],
        file_location='service_id/upload_id.pdf',
        filedata='pdf_data',
        metadata={'status': 'valid', 'page_count': '3', 'filename': 'my_doc'},
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


@pytest.mark.parametrize('original_address,expected_address', [
    ('The Queen, Buckingham Palace, SW1 1AA', 'The Queen, Buckingham Palace, SW1 1AA'),
    ('The Queen Buckingham Palace SW1 1AA', 'The Queen Buckingham Palace SW1 1AA'),
    ('The Queen,\nBuckingham Palace,\r\nSW1 1AA', 'The Queen, Buckingham Palace, SW1 1AA'),
    ('The Queen   ,,\nBuckingham Palace,\rSW1 1AA,', 'The Queen, Buckingham Palace, SW1 1AA'),
    ('  The Queen\n Buckingham Palace\n SW1 1AA', 'The Queen, Buckingham Palace, SW1 1AA'),
    ("The ’Queen\n Buckingham Palace\n SW1 1AA", "The 'Queen, Buckingham Palace, SW1 1AA"),
])
def test_format_recipient(original_address, expected_address):
    assert format_recipient(original_address) == expected_address
