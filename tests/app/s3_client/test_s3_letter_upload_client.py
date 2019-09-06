from flask import current_app

from app.s3_client.s3_letter_upload_client import upload_letter_to_s3


def test_upload_letter_to_s3(mocker):
    s3_mock = mocker.patch('app.s3_client.s3_letter_upload_client.utils_s3upload')

    upload_letter_to_s3('pdf_data', 'service_id/upload_id.pdf', 'valid')

    s3_mock.assert_called_once_with(
        bucket_name=current_app.config['TRANSIENT_UPLOADED_LETTERS'],
        file_location='service_id/upload_id.pdf',
        filedata='pdf_data',
        metadata={'status': 'valid'},
        region=current_app.config['AWS_REGION']
    )
