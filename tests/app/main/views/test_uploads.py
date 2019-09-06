from unittest.mock import Mock

import pytest
from flask import url_for
from requests import RequestException

from app.utils import normalize_spaces
from tests.conftest import SERVICE_ONE_ID


def test_get_upload_hub_page(client_request):
    page = client_request.get('main.uploads', service_id=SERVICE_ONE_ID)

    assert page.find('h1').text == 'Uploads'
    assert page.find('a', text='Upload a letter').attrs['href'] == url_for(
        'main.upload_letter', service_id=SERVICE_ONE_ID
    )


def test_get_upload_letter(client_request):
    page = client_request.get('main.upload_letter', service_id=SERVICE_ONE_ID)

    assert page.find('h1').text == 'Upload a letter'
    assert page.find('input', class_='file-upload-field')
    assert page.select('button[type=submit]')


def test_post_upload_letter_redirects_for_valid_file(mocker, client_request):
    mocker.patch('uuid.uuid4', return_value='fake-uuid')
    antivirus_mock = mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=True)
    mocker.patch('app.main.views.uploads.sanitise_letter', return_value=Mock(content='The sanitised content'))
    mock_s3 = mocker.patch('app.main.views.uploads.upload_letter_to_s3')

    with open('tests/test_pdf_files/one_page_pdf.pdf', 'rb') as file:
        page = client_request.post(
            'main.upload_letter',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _follow_redirects=True,
        )
    assert antivirus_mock.called

    mock_s3.assert_called_once_with(
        'The sanitised content',
        'service-{}/fake-uuid.pdf'.format(SERVICE_ONE_ID),
        'valid',
    )

    assert page.find('h1').text == 'tests/test_pdf_files/one_page_pdf.pdf'
    assert not page.find(id='validation-error-message')


def test_post_upload_letter_shows_error_when_file_is_not_a_pdf(client_request):
    with open('tests/non_spreadsheet_files/actually_a_png.csv', 'rb') as file:
        page = client_request.post(
            'main.upload_letter',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _expected_status=200
        )
    assert page.find('span', class_='error-message').text.strip() == "Letters must be saved as a PDF"


def test_post_upload_letter_shows_error_when_no_file_uploaded(client_request):
    page = client_request.post(
        'main.upload_letter',
        service_id=SERVICE_ONE_ID,
        _data={'file': ''},
        _expected_status=200
    )
    assert page.find('span', class_='error-message').text.strip() == "You need to upload a file to submit"


def test_post_upload_letter_shows_error_when_file_contains_virus(mocker, client_request):
    mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=False)

    with open('tests/test_pdf_files/one_page_pdf.pdf', 'rb') as file:
        page = client_request.post(
            'main.upload_letter',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _expected_status=400
        )
    assert page.find('h1').text == 'Upload a letter'
    assert normalize_spaces(page.select('.banner-dangerous')[0].text) == 'Your file has failed the virus check'


def test_post_choose_upload_file_when_file_is_too_big(mocker, client_request):
    mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=True)

    with open('tests/test_pdf_files/big.pdf', 'rb') as file:
        page = client_request.post(
            'main.upload_letter',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _expected_status=400
        )
    assert page.find('h1').text == 'Upload a letter'
    assert normalize_spaces(page.select('.banner-dangerous')[0].text) == 'Your file must be smaller than 2MB'


def test_post_choose_upload_file_when_file_is_malformed(mocker, client_request):
    mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=True)

    with open('tests/test_pdf_files/no_eof_marker.pdf', 'rb') as file:
        page = client_request.post(
            'main.upload_letter',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _expected_status=400
        )
    assert page.find('h1').text == 'Upload a letter'
    assert normalize_spaces(page.select('.banner-dangerous')[0].text) == 'Your file must be a valid PDF'


def test_post_upload_letter_with_invalid_file(mocker, client_request):
    mocker.patch('uuid.uuid4', return_value='fake-uuid')
    mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=True)
    mock_s3 = mocker.patch('app.main.views.uploads.upload_letter_to_s3')

    mock_sanitise_response = Mock()
    mock_sanitise_response.raise_for_status.side_effect = RequestException(response=Mock(status_code=400))
    mocker.patch('app.main.views.uploads.sanitise_letter', return_value=mock_sanitise_response)

    with open('tests/test_pdf_files/one_page_pdf.pdf', 'rb') as file:
        file_contents = file.read()
        file.seek(0)

        page = client_request.post(
            'main.upload_letter',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _follow_redirects=True
        )

        mock_s3.assert_called_once_with(
            file_contents,
            'service-{}/fake-uuid.pdf'.format(SERVICE_ONE_ID),
            'invalid',
        )

    assert page.find('h1').text == 'tests/test_pdf_files/one_page_pdf.pdf'
    assert normalize_spaces(
        page.find(id='validation-error-message').text
    ) == 'Validation failed'


def test_post_upload_letter_does_not_upload_to_s3_if_template_preview_raises_unknown_error(mocker, client_request):
    mocker.patch('uuid.uuid4', return_value='fake-uuid')
    mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=True)
    mock_s3 = mocker.patch('app.main.views.uploads.upload_letter_to_s3')

    mocker.patch('app.main.views.uploads.sanitise_letter', side_effect=RequestException())

    with pytest.raises(RequestException):
        with open('tests/test_pdf_files/one_page_pdf.pdf', 'rb') as file:
            client_request.post(
                'main.upload_letter',
                service_id=SERVICE_ONE_ID,
                _data={'file': file},
                _follow_redirects=True
            )

    assert not mock_s3.called


def test_uploaded_letter_preview(client_request):
    page = client_request.get(
        'main.uploaded_letter_preview',
        service_id=SERVICE_ONE_ID,
        file_id='fake-uuid',
        original_filename='my_letter.pdf',
    )

    assert page.find('h1').text == 'my_letter.pdf'
