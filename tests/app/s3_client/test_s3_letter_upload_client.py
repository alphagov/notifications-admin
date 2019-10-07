from flask import current_app

from app.s3_client.s3_letter_upload_client import upload_letter_to_s3


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
