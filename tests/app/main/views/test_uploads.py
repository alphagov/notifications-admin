import re
import uuid
from io import BytesIO
from unittest.mock import ANY, Mock

import pytest
from flask import make_response, url_for
from freezegun import freeze_time
from requests import RequestException

from app.main.views.uploads import format_recipient
from app.s3_client.s3_letter_upload_client import LetterMetadata
from app.utils import normalize_spaces
from tests.conftest import (
    SERVICE_ONE_ID,
    create_active_caseworking_user,
    create_active_user_with_permissions,
    create_platform_admin_user,
)


@pytest.mark.parametrize('extra_permissions', (
    pytest.param(
        [],
        marks=pytest.mark.xfail(raises=AssertionError),
    ),
    pytest.param(
        ['upload_letters'],
        marks=pytest.mark.xfail(raises=AssertionError),
    ),
    ['letter'],
    ['letter', 'upload_letters'],
))
def test_upload_letters_button_only_with_letters_permission(
    client_request,
    service_one,
    mock_get_uploads,
    mock_get_jobs,
    mock_get_no_contact_lists,
    extra_permissions,
):
    service_one['permissions'] += extra_permissions
    page = client_request.get('main.uploads', service_id=SERVICE_ONE_ID)
    assert page.find('a', text=re.compile('Upload a letter'))


@pytest.mark.parametrize('user', (
    create_platform_admin_user(),
    create_active_user_with_permissions(),
))
def test_all_users_have_upload_contact_list(
    client_request,
    mock_get_uploads,
    mock_get_jobs,
    mock_get_no_contact_lists,
    user,
):
    client_request.login(user)
    page = client_request.get('main.uploads', service_id=SERVICE_ONE_ID)
    button = page.find('a', text=re.compile('Upload an emergency contact list'))
    assert button
    assert button['href'] == url_for(
        'main.upload_contact_list', service_id=SERVICE_ONE_ID,
    )


@pytest.mark.parametrize('extra_permissions, expected_empty_message', (
    ([], (
        'You have not uploaded any files recently.'
    )),
    (['letter'], (
        'You have not uploaded any files recently. '
        'Upload a letter and Notify will print, pack and post it for you.'
    )),
))
def test_get_upload_hub_with_no_uploads(
    mocker,
    client_request,
    service_one,
    mock_get_no_uploads,
    mock_get_no_contact_lists,
    extra_permissions,
    expected_empty_message,
):
    mocker.patch('app.job_api_client.get_jobs', return_value={'data': []})
    service_one['permissions'] += extra_permissions
    page = client_request.get('main.uploads', service_id=SERVICE_ONE_ID)
    assert normalize_spaces(' '.join(
        paragraph.text for paragraph in page.select('main p')
    )) == expected_empty_message
    assert not page.select('.file-list-filename')


@freeze_time('2017-10-10 10:10:10')
def test_get_upload_hub_page(
    mocker,
    client_request,
    service_one,
    mock_get_uploads,
    mock_get_no_contact_lists,
):
    mocker.patch('app.job_api_client.get_jobs', return_value={'data': []})
    service_one['permissions'] += ['letter', 'upload_letters']
    page = client_request.get('main.uploads', service_id=SERVICE_ONE_ID)
    assert page.find('h1').text == 'Uploads'
    assert page.find('a', text=re.compile('Upload a letter')).attrs['href'] == url_for(
        'main.upload_letter', service_id=SERVICE_ONE_ID
    )

    uploads = page.select('tbody tr')

    assert len(uploads) == 3

    assert normalize_spaces(uploads[0].text.strip()) == (
        'Uploaded letters '
        'Printing today at 5:30pm '
        '33 letters'
    )
    assert uploads[0].select_one('a.file-list-filename-large')['href'] == url_for(
        'main.uploaded_letters',
        service_id=SERVICE_ONE_ID,
        letter_print_day='2017-10-10',
    )

    assert normalize_spaces(uploads[1].text.strip()) == (
        'some.csv '
        'Sent 1 January 2016 at 11:09am '
        '0 sending 8 delivered 2 failed'
    )
    assert uploads[1].select_one('a.file-list-filename-large')['href'] == (
        '/services/{}/jobs/job_id_1'.format(SERVICE_ONE_ID)
    )

    assert normalize_spaces(uploads[2].text.strip()) == (
        'some.pdf '
        'Sent 1 January 2016 at 11:09am '
        'Firstname Lastname '
        '123 Example Street'
    )
    assert normalize_spaces(str(uploads[2].select_one('.govuk-body'))) == (
        '<p class="govuk-body letter-recipient-summary"> '
        'Firstname Lastname<br/> '
        '123 Example Street<br/> '
        '</p>'
    )
    assert uploads[2].select_one('a.file-list-filename-large')['href'] == (
        '/services/{}/notification/letter_id_1'.format(SERVICE_ONE_ID)
    )


@freeze_time('2020-02-02 14:00')
def test_get_uploaded_letters(
    mocker,
    client_request,
    service_one,
    mock_get_uploaded_letters,
):
    page = client_request.get(
        'main.uploaded_letters',
        service_id=SERVICE_ONE_ID,
        letter_print_day='2020-02-02'
    )
    assert page.select_one('.govuk-back-link')['href'] == url_for(
        'main.uploads',
        service_id=SERVICE_ONE_ID,
    )
    assert normalize_spaces(
        page.select_one('h1').text
    ) == (
        'Uploaded letters'
    )
    assert normalize_spaces(
        page.select('main p')[0].text
    ) == (
        '1,234 letters'
    )
    assert normalize_spaces(
        page.select('main p')[1].text
    ) == (
        'Printing starts today at 5:30pm'
    )

    assert [
        normalize_spaces(row.text)
        for row in page.select('tbody tr')
    ] == [
        (
            'Homer-Simpson.pdf '
            '742 Evergreen Terrace '
            '2 February at 1:59pm'
        ),
        (
            'Kevin-McCallister.pdf '
            '671 Lincoln Avenue, Winnetka '
            '2 February at 12:59pm'
        ),
    ]

    assert [
        link['href'] for link in page.select('tbody tr a')
    ] == [
        url_for(
            'main.view_notification',
            service_id=SERVICE_ONE_ID,
            notification_id='03e34025-be54-4d43-8e6a-fb1ea0fd1f29',
            from_uploaded_letters='2020-02-02',
        ),
        url_for(
            'main.view_notification',
            service_id=SERVICE_ONE_ID,
            notification_id='fc090d91-e761-4464-9041-9c4594c96a35',
            from_uploaded_letters='2020-02-02',
        ),
    ]

    next_page_link = page.select_one('a[rel=next]')
    prev_page_link = page.select_one('a[rel=previous]')
    assert next_page_link['href'] == url_for(
        'main.uploaded_letters', service_id=SERVICE_ONE_ID, letter_print_day='2020-02-02', page=2
    )
    assert normalize_spaces(next_page_link.text) == (
        'Next page '
        'page 2'
    )
    assert prev_page_link['href'] == url_for(
        'main.uploaded_letters', service_id=SERVICE_ONE_ID, letter_print_day='2020-02-02', page=0
    )
    assert normalize_spaces(prev_page_link.text) == (
        'Previous page '
        'page 0'
    )

    mock_get_uploaded_letters.assert_called_once_with(
        SERVICE_ONE_ID,
        letter_print_day='2020-02-02',
        page=1,
    )


@freeze_time('2020-02-02 14:00')
def test_get_empty_uploaded_letters_page(
    mocker,
    client_request,
    service_one,
    mock_get_no_uploaded_letters,
):
    page = client_request.get(
        'main.uploaded_letters',
        service_id=SERVICE_ONE_ID,
        letter_print_day='2020-02-02'
    )
    page.select_one('main table')

    assert not page.select('tbody tr')
    assert not page.select_one('a[rel=next]')
    assert not page.select_one('a[rel=previous]')


@freeze_time('2020-02-02')
def test_get_uploaded_letters_passes_through_page_argument(
    mocker,
    client_request,
    service_one,
    mock_get_uploaded_letters,
):
    client_request.get(
        'main.uploaded_letters',
        service_id=SERVICE_ONE_ID,
        letter_print_day='2020-02-02',
        page=99,
    )
    mock_get_uploaded_letters.assert_called_once_with(
        SERVICE_ONE_ID,
        letter_print_day='2020-02-02',
        page=99,
    )


def test_get_uploaded_letters_404s_for_bad_page_arguments(
    mocker,
    client_request,
):
    client_request.get(
        'main.uploaded_letters',
        service_id=SERVICE_ONE_ID,
        letter_print_day='2020-02-02',
        page='one',
        _expected_status=404,
    )


def test_get_uploaded_letters_404s_for_invalid_date(
    mocker,
    client_request,
):
    client_request.get(
        'main.uploaded_letters',
        service_id=SERVICE_ONE_ID,
        letter_print_day='1234-56-78',
        _expected_status=404,
    )


def test_get_upload_letter(client_request):
    page = client_request.get('main.upload_letter', service_id=SERVICE_ONE_ID)

    assert page.find('h1').text == 'Upload a letter'
    assert page.find('input', class_='file-upload-field')
    assert page.select('main button[type=submit]')
    assert normalize_spaces(page.find('label', class_='file-upload-button').text) == 'Choose file'


@pytest.mark.parametrize('extra_permissions, expected_allow_international', (
    ([], False),
    (['international_letters'], True),
))
def test_post_upload_letter_redirects_for_valid_file(
    mocker,
    active_user_with_permissions,
    service_one,
    client_request,
    fake_uuid,
    extra_permissions,
    expected_allow_international,
):
    mocker.patch('uuid.uuid4', return_value=fake_uuid)
    antivirus_mock = mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=True)
    mock_sanitise = mocker.patch(
        'app.main.views.uploads.sanitise_letter',
        return_value=Mock(
            content='The sanitised content',
            json=lambda: {'file': 'VGhlIHNhbml0aXNlZCBjb250ZW50', 'recipient_address': 'The Queen'}
        )
    )
    mock_s3 = mocker.patch('app.main.views.uploads.upload_letter_to_s3')
    mocker.patch('app.main.views.uploads.get_letter_metadata', return_value=LetterMetadata({
        'filename': 'tests/test_pdf_files/one_page_pdf.pdf',
        'page_count': '1',
        'status': 'valid',
        'recipient': 'The Queen'
    }))
    mocker.patch('app.main.views.uploads.service_api_client.get_precompiled_template')

    service_one['restricted'] = False
    service_one['permissions'] += extra_permissions
    client_request.login(active_user_with_permissions, service=service_one)

    with open('tests/test_pdf_files/one_page_pdf.pdf', 'rb') as file:
        page = client_request.post(
            'main.upload_letter',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _follow_redirects=True,
        )
    assert antivirus_mock.called

    mock_s3.assert_called_once_with(
        b'The sanitised content',
        file_location='service-{}/{}.pdf'.format(SERVICE_ONE_ID, fake_uuid),
        status='valid',
        page_count=1,
        filename='tests/test_pdf_files/one_page_pdf.pdf',
        recipient='The Queen',
    )
    mock_sanitise.assert_called_once_with(
        ANY,
        allow_international_letters=expected_allow_international,
    )

    assert 'The Queen' in page.find('div', class_='js-stick-at-bottom-when-scrolling').text
    assert page.find('h1').text == 'tests/test_pdf_files/one_page_pdf.pdf'
    assert not page.find(id='validation-error-message')

    assert not page.find('input', {'name': 'file_id'})
    assert normalize_spaces(page.select('main button[type=submit]')[0].text) == 'Send 1 letter'


def test_post_upload_letter_shows_letter_preview_for_valid_file(
    mocker,
    active_user_with_permissions,
    service_one,
    client_request,
    fake_uuid,
):
    letter_template = {'template_type': 'letter',
                       'reply_to_text': '',
                       'postage': 'second',
                       'subject': 'hi',
                       'content': 'my letter'}

    mocker.patch('uuid.uuid4', return_value=fake_uuid)
    mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=True)
    mocker.patch(
        'app.main.views.uploads.sanitise_letter',
        return_value=Mock(
            content='The sanitised content',
            json=lambda: {'file': 'VGhlIHNhbml0aXNlZCBjb250ZW50', 'recipient_address': 'The Queen'}
        )
    )
    mocker.patch('app.main.views.uploads.upload_letter_to_s3')
    mocker.patch('app.main.views.uploads.pdf_page_count', return_value=3)
    mocker.patch('app.main.views.uploads.get_letter_metadata', return_value=LetterMetadata({
        'filename': 'tests/test_pdf_files/one_page_pdf.pdf',
        'page_count': '3',
        'status': 'valid',
        'recipient': 'The Queen'
    }))
    mocker.patch('app.main.views.uploads.service_api_client.get_precompiled_template', return_value=letter_template)

    service_one['restricted'] = False
    client_request.login(active_user_with_permissions, service=service_one)

    with open('tests/test_pdf_files/one_page_pdf.pdf', 'rb') as file:
        page = client_request.post(
            'main.upload_letter',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _follow_redirects=True,
        )

    assert page.find('h1').text == 'tests/test_pdf_files/one_page_pdf.pdf'
    assert len(page.select('.letter-postage')) == 0
    # Check postage radios exists and second class is checked by default
    assert page.find('input', id="postage-0", value="first")
    assert page.find('input', id="postage-1", value="second").has_attr('checked')

    letter_images = page.select('main img')
    assert len(letter_images) == 3

    for page_no, img in enumerate(letter_images, start=1):
        assert img['src'] == url_for(
            '.view_letter_upload_as_preview',
            service_id=SERVICE_ONE_ID,
            file_id=fake_uuid,
            page=page_no)


def test_post_upload_letter_shows_error_when_file_is_not_a_pdf(client_request):
    with open('tests/non_spreadsheet_files/actually_a_png.csv', 'rb') as file:
        page = client_request.post(
            'main.upload_letter',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _expected_status=200
        )
    assert page.find('h1').text == 'Wrong file type'
    assert page.find('div', class_='banner-dangerous').find('p').text == 'Save your letter as a PDF and try again.'
    assert normalize_spaces(page.find('label', class_='file-upload-button').text) == 'Upload your file again'


def test_post_upload_letter_shows_error_when_no_file_uploaded(client_request):
    page = client_request.post(
        'main.upload_letter',
        service_id=SERVICE_ONE_ID,
        _data={'file': ''},
        _expected_status=200
    )
    assert page.find('div', class_='banner-dangerous').find('h1').text == 'You need to choose a file to upload'
    assert normalize_spaces(page.find('label', class_='file-upload-button').text) == 'Upload your file again'


def test_post_upload_letter_shows_error_when_file_contains_virus(mocker, client_request):
    mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=False)

    with open('tests/test_pdf_files/one_page_pdf.pdf', 'rb') as file:
        page = client_request.post(
            'main.upload_letter',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _expected_status=400
        )
    assert page.find('div', class_='banner-dangerous').find('h1').text == 'Your file contains a virus'
    assert normalize_spaces(page.find('label', class_='file-upload-button').text) == 'Upload your file again'


def test_post_choose_upload_file_when_file_is_too_big(mocker, client_request):
    mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=True)

    with open('tests/test_pdf_files/big.pdf', 'rb') as file:
        page = client_request.post(
            'main.upload_letter',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _expected_status=400
        )
    assert page.find('div', class_='banner-dangerous').find('h1').text == 'Your file is too big'
    assert page.find('div', class_='banner-dangerous').find('p').text == 'Files must be smaller than 2MB.'
    assert normalize_spaces(page.find('label', class_='file-upload-button').text) == 'Upload your file again'


def test_post_choose_upload_file_when_file_is_malformed(mocker, client_request):
    mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=True)

    with open('tests/test_pdf_files/no_eof_marker.pdf', 'rb') as file:
        page = client_request.post(
            'main.upload_letter',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _expected_status=400
        )
    assert page.find('div', class_='banner-dangerous').find('h1').text == "There’s a problem with your file"
    assert page.find(
        'div', class_='banner-dangerous'
    ).find('p').text == 'Notify cannot read this PDF.Save a new copy of your file and try again.'
    assert normalize_spaces(page.find('label', class_='file-upload-button').text) == 'Upload your file again'


def test_post_upload_letter_with_invalid_file(mocker, client_request, fake_uuid):
    mocker.patch('uuid.uuid4', return_value=fake_uuid)
    mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=True)
    mock_s3 = mocker.patch('app.main.views.uploads.upload_letter_to_s3')

    mock_sanitise_response = Mock()
    mock_sanitise_response.raise_for_status.side_effect = RequestException(response=Mock(status_code=400))
    mock_sanitise_response.json = lambda: {
        "message": "content-outside-printable-area",
        "invalid_pages": [1]
    }
    mocker.patch('app.main.views.uploads.sanitise_letter', return_value=mock_sanitise_response)
    mocker.patch('app.main.views.uploads.service_api_client.get_precompiled_template')
    mocker.patch('app.main.views.uploads.get_letter_metadata', return_value=LetterMetadata({
        'filename': 'tests/test_pdf_files/one_page_pdf.pdf', 'page_count': '1', 'status': 'invalid',
        'message': 'content-outside-printable-area', 'invalid_pages': '[1]'}))

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
            file_location='service-{}/{}.pdf'.format(SERVICE_ONE_ID, fake_uuid),
            status='invalid',
            page_count=1,
            filename='tests/test_pdf_files/one_page_pdf.pdf',
            invalid_pages=[1],
            message='content-outside-printable-area'
        )

    assert page.find('div', class_='banner-dangerous').find('h1', {"data-error-type": 'content-outside-printable-area'})
    assert not page.find('button', {'class': 'page-footer__button', 'type': 'submit'})


def test_post_upload_letter_shows_letter_preview_for_invalid_file(mocker, client_request, fake_uuid):
    letter_template = {'template_type': 'letter',
                       'reply_to_text': '',
                       'postage': 'first',
                       'subject': 'hi',
                       'content': 'my letter'}

    mocker.patch('uuid.uuid4', return_value=fake_uuid)
    mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=True)
    mocker.patch('app.main.views.uploads.upload_letter_to_s3')
    mock_sanitise_response = Mock()
    mock_sanitise_response.raise_for_status.side_effect = RequestException(response=Mock(status_code=400))
    mock_sanitise_response.json = lambda: {"message": "template preview error", "recipient_address": "The Queen"}
    mocker.patch('app.main.views.uploads.sanitise_letter', return_value=mock_sanitise_response)
    mocker.patch('app.main.views.uploads.service_api_client.get_precompiled_template', return_value=letter_template)
    mocker.patch('app.main.views.uploads.get_letter_metadata', return_value=LetterMetadata({
        'filename': 'tests/test_pdf_files/one_page_pdf.pdf', 'page_count': '1', 'status': 'invalid',
        'message': 'template-preview-error'}))

    with open('tests/test_pdf_files/one_page_pdf.pdf', 'rb') as file:
        page = client_request.post(
            'main.upload_letter',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _follow_redirects=True,
        )

    assert 'The Queen' not in page.text
    assert len(page.select('.letter-postage')) == 0

    assert page.find("a", {"class": "govuk-back-link"})["href"] == "/services/{}/upload-letter".format(SERVICE_ONE_ID)
    assert page.find("label", {"class": "file-upload-button"})

    letter_images = page.select('main img')
    assert len(letter_images) == 1
    assert letter_images[0]['src'] == url_for(
        '.view_letter_upload_as_preview',
        service_id=SERVICE_ONE_ID,
        file_id=fake_uuid,
        page=1
    )


def test_post_upload_letter_does_not_upload_to_s3_if_template_preview_raises_unknown_error(
    mocker,
    client_request,
    fake_uuid,
):
    mocker.patch('uuid.uuid4', return_value=fake_uuid)
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


def test_uploaded_letter_preview(
    mocker,
    active_user_with_permissions,
    service_one,
    client_request,
    fake_uuid,
):
    mocker.patch('app.main.views.uploads.service_api_client')
    mocker.patch('app.main.views.uploads.get_letter_metadata', return_value=LetterMetadata({
        'filename': 'my_encoded_filename%C2%A3.pdf',
        'page_count': '1',
        'status': 'valid',
        'recipient': 'Bugs Bunny%0A123 Big Hole%0DLooney Town'  # 'Bugs Bunny%0A123 Big Hole\rLooney Town' url encoded
    }))

    service_one['restricted'] = False
    client_request.login(active_user_with_permissions, service=service_one)

    page = client_request.get(
        'main.uploaded_letter_preview',
        service_id=SERVICE_ONE_ID,
        file_id=fake_uuid,
    )

    assert page.find('h1').text == 'my_encoded_filename£.pdf'
    assert page.find('div', class_='letter-sent')
    assert not page.find("label", {"class": "file-upload-button"})
    assert page.find('button', {'class': 'page-footer__button', 'type': 'submit'})


def test_uploaded_letter_preview_does_not_show_send_button_if_service_in_trial_mode(
    mocker,
    client_request,
    fake_uuid,
):
    mocker.patch('app.main.views.uploads.service_api_client')
    mocker.patch('app.main.views.uploads.get_letter_metadata', return_value=LetterMetadata({
        'filename': 'my_letter.pdf', 'page_count': '1', 'status': 'valid', 'recipient': 'The Queen'}))

    # client_request uses service_one, which is in trial mode
    page = client_request.get(
        'main.uploaded_letter_preview',
        service_id=SERVICE_ONE_ID,
        file_id=fake_uuid,
        original_filename='my_letter.pdf',
        page_count=1,
        status='valid',
        error={},
        _test_page_title=False,
    )

    assert normalize_spaces(page.find('h1').text) == 'You cannot send this letter'
    assert page.find('div', class_='letter-sent')
    assert normalize_spaces(
        page.select_one('.js-stick-at-bottom-when-scrolling p').text
    ) == (
        'Recipient: The Queen'
    )
    assert not page.find('form')
    assert len(page.select('main button[type=submit]')) == 0


@pytest.mark.parametrize('invalid_pages, page_requested, overlay_expected', (
    ('[1, 2]', 1, True),
    ('[1, 2]', 2, True),
    ('[1, 2]', 3, False),
    ('[]', 1, False),
))
def test_uploaded_letter_preview_image_shows_overlay_when_content_outside_printable_area_on_a_page(
    mocker,
    logged_in_client,
    mock_get_service,
    fake_uuid,
    invalid_pages,
    page_requested,
    overlay_expected,
):
    mocker.patch(
        'app.main.views.uploads.get_letter_pdf_and_metadata',
        return_value=('pdf_file', {
            'message': 'content-outside-printable-area',
            'invalid_pages': invalid_pages,
        })
    )
    template_preview_mock_valid = mocker.patch(
        'app.main.views.uploads.TemplatePreview.from_valid_pdf_file',
        return_value=make_response('page.html', 200)
    )
    template_preview_mock_invalid = mocker.patch(
        'app.main.views.uploads.TemplatePreview.from_invalid_pdf_file',
        return_value=make_response('page.html', 200)
    )

    logged_in_client.get(
        url_for(
            'main.view_letter_upload_as_preview',
            file_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            page=page_requested,
        )
    )

    if overlay_expected:
        template_preview_mock_invalid.assert_called_once_with('pdf_file', page_requested)
        assert template_preview_mock_valid.called is False
    else:
        template_preview_mock_valid.assert_called_once_with('pdf_file', page_requested)
        assert template_preview_mock_invalid.called is False


@pytest.mark.parametrize(
    'metadata', [
        {'message': 'letter-not-a4-portrait-oriented'},
        {'message': 'letter-too-long'},
        {},
    ]
)
def test_uploaded_letter_preview_image_does_not_show_overlay_if_no_content_outside_printable_area(
    mocker,
    logged_in_client,
    mock_get_service,
    metadata,
    fake_uuid,
):
    mocker.patch(
        'app.main.views.uploads.get_letter_pdf_and_metadata',
        return_value=('pdf_file', metadata)
    )
    template_preview_mock = mocker.patch(
        'app.main.views.uploads.TemplatePreview.from_valid_pdf_file',
        return_value=make_response('page.html', 200))

    logged_in_client.get(
        url_for('main.view_letter_upload_as_preview', file_id=fake_uuid, service_id=SERVICE_ONE_ID, page=1)
    )

    template_preview_mock.assert_called_once_with('pdf_file', 1)


def test_uploaded_letter_preview_image_400s_for_bad_page_type(
    client_request,
    fake_uuid,
):
    client_request.get(
        'main.view_letter_upload_as_preview',
        file_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        page='foo',
        _test_page_title=False,
        _expected_status=400,
    )


def test_send_uploaded_letter_sends_letter_and_redirects_to_notification_page(mocker, service_one, client_request):
    metadata = LetterMetadata({'filename': 'my_file.pdf', 'page_count': '1', 'status': 'valid', 'recipient': 'address'})

    mocker.patch('app.main.views.uploads.get_letter_pdf_and_metadata', return_value=('file', metadata))
    mock_send = mocker.patch('app.main.views.uploads.notification_api_client.send_precompiled_letter')
    mocker.patch('app.main.views.uploads.get_letter_metadata', return_value=metadata)

    service_one['permissions'] = ['letter', 'upload_letters']
    file_id = 'abcd-1234'

    client_request.post(
        'main.send_uploaded_letter',
        service_id=SERVICE_ONE_ID,
        _data={'filename': 'my_file.pdf', 'file_id': file_id, 'postage': 'first'},
        _expected_redirect=url_for(
            'main.view_notification',
            service_id=SERVICE_ONE_ID,
            notification_id=file_id,
            _external=True
        )
    )
    mock_send.assert_called_once_with(SERVICE_ONE_ID, 'my_file.pdf', file_id, 'first', 'address')


@pytest.mark.parametrize('form_data', (
    {'filename': 'my_file.pdf', 'postage': 'first'},
    {'filename': 'my_file.pdf', 'postage': 'first', 'file_id': 'Ignored in favour of URL'},
))
def test_send_uploaded_letter_accepts_file_id_in_url(
    mocker,
    service_one,
    client_request,
    fake_uuid,
    form_data,
):
    metadata = LetterMetadata({'filename': 'my_file.pdf', 'page_count': '1', 'status': 'valid', 'recipient': 'address'})

    mocker.patch('app.main.views.uploads.get_letter_pdf_and_metadata', return_value=('file', metadata))
    mock_send = mocker.patch('app.main.views.uploads.notification_api_client.send_precompiled_letter')
    mocker.patch('app.main.views.uploads.get_letter_metadata', return_value=metadata)

    service_one['permissions'] = ['letter', 'upload_letters']

    client_request.post(
        'main.send_uploaded_letter',
        service_id=SERVICE_ONE_ID,
        file_id=fake_uuid,
        _data=form_data,
        _expected_redirect=url_for(
            'main.view_notification',
            service_id=SERVICE_ONE_ID,
            notification_id=fake_uuid,
            _external=True
        )
    )
    mock_send.assert_called_once_with(SERVICE_ONE_ID, 'my_file.pdf', fake_uuid, 'first', 'address')


def test_send_uploaded_letter_needs_file_id_in_form_if_not_in_url(
    mocker,
    service_one,
    client_request,
    mock_template_preview,
    fake_uuid,
):
    metadata = LetterMetadata({'filename': 'my_file.pdf', 'page_count': '1', 'status': 'valid', 'recipient': 'address'})

    mock_send = mocker.patch('app.main.views.uploads.notification_api_client.send_precompiled_letter')
    mocker.patch('app.main.views.uploads.get_letter_metadata', return_value=metadata)
    mocker.patch('app.main.views.uploads.service_api_client.get_precompiled_template')

    service_one['permissions'] = ['letter', 'upload_letters']

    client_request.post(
        'main.send_uploaded_letter',
        service_id=SERVICE_ONE_ID,
        _data={'filename': 'my_file.pdf', 'postage': 'first'},
        _expected_status=200,
        _expected_redirect=None,
    )
    assert mock_send.called is False


@pytest.mark.parametrize('permissions', [
    ['email'],
    ['letter'],
    ['upload_letters'],
])
def test_send_uploaded_letter_when_service_does_not_have_correct_permissions(
    mocker,
    service_one,
    client_request,
    permissions,
):
    mocker.patch('app.main.views.uploads.get_letter_pdf_and_metadata', return_value=('file', {'status': 'valid'}))
    mock_send = mocker.patch('app.main.views.uploads.notification_api_client.send_precompiled_letter')

    service_one['permissions'] = permissions
    file_id = 'abcd-1234'

    client_request.post(
        'main.send_uploaded_letter',
        service_id=SERVICE_ONE_ID,
        _data={'filename': 'my_file.pdf', 'file_id': file_id, 'postage': 'first'},
        _expected_status=403
    )
    assert not mock_send.called


def test_send_uploaded_letter_when_metadata_states_pdf_is_invalid(mocker, service_one, client_request):
    mock_send = mocker.patch('app.main.views.uploads.notification_api_client.send_precompiled_letter')
    mocker.patch(
        'app.main.views.uploads.get_letter_metadata',
        return_value=LetterMetadata(
            {
                'filename': 'my_file.pdf', 'page_count': '3', 'status': 'invalid',
                'message': 'error', 'invalid_pages': '[1]'
            }
        )
    )

    service_one['permissions'] = ['letter', 'upload_letters']
    file_id = 'abcd-1234'

    client_request.post(
        'main.send_uploaded_letter',
        service_id=SERVICE_ONE_ID,
        _data={'filename': 'my_file.pdf', 'file_id': file_id},
        _expected_status=403
    )
    assert not mock_send.called


@pytest.mark.parametrize('original_address,expected_address', [
    ('The Queen, Buckingham Palace, SW1 1AA', 'The Queen, Buckingham Palace, SW1 1AA'),
    ('The Queen Buckingham Palace SW1 1AA', 'The Queen Buckingham Palace SW1 1AA'),
    ('The Queen,\nBuckingham Palace,\r\nSW1 1AA', 'The Queen, Buckingham Palace, SW1 1AA'),
    ('The Queen   ,,\nBuckingham Palace,\rSW1 1AA,', 'The Queen, Buckingham Palace, SW1 1AA'),
    ('  The Queen\n Buckingham Palace\n SW1 1AA', 'The Queen, Buckingham Palace, SW1 1AA'),
    ('', ''),
])
def test_format_recipient(original_address, expected_address):
    assert format_recipient(original_address) == expected_address


@pytest.mark.parametrize('user', (
    create_active_caseworking_user(),
    create_active_user_with_permissions(),
))
@freeze_time("2012-12-12 12:12")
def test_uploads_page_shows_scheduled_jobs(
    mocker,
    client_request,
    mock_get_no_uploads,
    mock_get_jobs,
    mock_get_no_contact_lists,
    user,
):
    client_request.login(user)
    page = client_request.get('main.uploads', service_id=SERVICE_ONE_ID)

    assert [
        normalize_spaces(row.text) for row in page.select('tr')
    ] == [
        (
            'File Status'
        ),
        (
            'even_later.csv '
            'Sending 1 January 2016 at 11:09pm '
            '1 text message waiting to send'
        ),
        (
            'send_me_later.csv '
            'Sending 1 January 2016 at 11:09am '
            '1 text message waiting to send'
        ),
    ]
    assert not page.select('.table-empty-message')


@freeze_time('2020-03-15')
def test_uploads_page_shows_contact_lists_first(
    mocker,
    client_request,
    mock_get_no_uploads,
    mock_get_jobs,
    mock_get_contact_lists,
):
    page = client_request.get('main.uploads', service_id=SERVICE_ONE_ID)

    assert [
        normalize_spaces(row.text) for row in page.select('tr')
    ] == [
        (
            'File Status'
        ),
        (
            'phone number list.csv '
            'Uploaded 13 March at 1:00pm '
            '123 saved phone numbers'
        ),
        (
            'EmergencyContactList.xls '
            'Uploaded 13 March at 10:59am '
            '100 saved email addresses'
        ),
        (
            'even_later.csv '
            'Sending 1 January 2016 at 11:09pm '
            '1 text message waiting to send'
        ),
        (
            'send_me_later.csv '
            'Sending 1 January 2016 at 11:09am '
            '1 text message waiting to send'
        ),
    ]
    assert page.select_one('.file-list-filename-large')['href'] == url_for(
        'main.contact_list',
        service_id=SERVICE_ONE_ID,
        contact_list_id='d7b0bd1a-d1c7-4621-be5c-3c1b4278a2ad',
    )


def test_get_uploads_shows_pagination(
    client_request,
    active_user_with_permissions,
    mock_get_jobs,
    mock_get_uploads,
    mock_get_no_contact_lists,
):
    page = client_request.get('main.uploads', service_id=SERVICE_ONE_ID)

    assert normalize_spaces(page.select_one('.next-page').text) == (
        'Next page '
        'page 2'
    )
    assert normalize_spaces(page.select_one('.previous-page').text) == (
        'Previous page '
        'page 0'
    )


def test_upload_contact_list_page(client_request):
    page = client_request.get(
        'main.upload_contact_list',
        service_id=SERVICE_ONE_ID,
    )
    assert 'action' not in page.select_one('form')
    assert page.select_one('form input')['name'] == 'file'
    assert page.select_one('form input')['type'] == 'file'

    assert normalize_spaces(page.select('.spreadsheet')[0].text) == (
        'Example A '
        '1 email address '
        '2 test@example.gov.uk'
    )
    assert normalize_spaces(page.select('.spreadsheet')[1].text) == (
        'Example A '
        '1 phone number '
        '2 07700 900123'
    )


@pytest.mark.parametrize('file_contents, expected_error, expected_thead, expected_tbody,', [
    (
        """
            telephone,name
            +447700900986
        """,
        (
            'Your file has too many columns '
            'It needs to have 1 column, called ‘email address’ or ‘phone number’. '
            'Right now it has 2 columns called ‘telephone’ and ‘name’. '
            'Skip to file contents'
        ),
        'Row in file 1 telephone name',
        '2 +447700900986',
    ),
    (
        """
            phone number, email address
            +447700900986, test@example.com
        """,
        (
            'Your file has too many columns '
            'It needs to have 1 column, called ‘email address’ or ‘phone number’. '
            'Right now it has 2 columns called ‘phone number’ and ‘email address’. '
            'Skip to file contents'
        ),
        'Row in file 1 phone number email address',
        '2 +447700900986 test@example.com',
    ),
    (
        """
            email address
            +447700900986
        """,
        (
            'There’s a problem with invalid.csv '
            'You need to fix 1 email address. '
            'Skip to file contents'
        ),
        'Row in file 1 email address',
        '2 Not a valid email address +447700900986',
    ),
    (
        """
            phone number
            test@example.com
        """,
        (
            'There’s a problem with invalid.csv '
            'You need to fix 1 phone number. '
            'Skip to file contents'
        ),
        'Row in file 1 phone number',
        '2 Must not contain letters or symbols test@example.com',
    ),
    (
        """
            phone number, phone number, PHONE_NUMBER
            +447700900111,+447700900222,+447700900333,
        """,
        (
            'Your file has too many columns '
            'It needs to have 1 column, called ‘email address’ or ‘phone number’. '
            'Right now it has 3 columns called ‘phone number’, ‘phone number’ and ‘PHONE_NUMBER’. '
            'Skip to file contents'
        ),
        'Row in file 1 phone number phone number PHONE_NUMBER',
        '2 +447700900333 +447700900333 +447700900333',
    ),
    (
        """
            phone number
        """,
        (
            'Your file is missing some rows '
            'It needs at least one row of data. '
            'Skip to file contents'
        ),
        'Row in file 1 phone number',
        '',
    ),
    (
        "+447700900986",
        (
            'Your file is missing some rows '
            'It needs at least one row of data, in a column called '
            '‘email address’ or ‘phone number’. '
            'Skip to file contents'
        ),
        'Row in file 1 +447700900986',
        '',
    ),
    (
        "",
        (
            'Your file is missing some rows '
            'It needs at least one row of data, in a column called '
            '‘email address’ or ‘phone number’. '
            'Skip to file contents'
        ),
        'Row in file 1',
        '',
    ),
    (
        """
            phone number
            +447700900986

            +447700900986
        """,
        (
            'There’s a problem with invalid.csv '
            'You need to enter missing data in 1 row. '
            'Skip to file contents'
        ),
        'Row in file 1 phone number',
        (
            '3 Missing'
        )
    ),
    (
        """
            phone number
            +447700900
        """,
        (
            'There’s a problem with invalid.csv '
            'You need to fix 1 phone number. '
            'Skip to file contents'
        ),
        'Row in file 1 phone number',
        '2 Not enough digits +447700900',
    ),
    (
        """
            email address
            ok@example.com
            bad@example1
            bad@example2
        """,
        (
            'There’s a problem with invalid.csv '
            'You need to fix 2 email addresses. '
            'Skip to file contents'
        ),
        'Row in file 1 email address',
        (
            '3 Not a valid email address bad@example1 '
            '4 Not a valid email address bad@example2'
        ),
    ),
])
def test_upload_csv_file_shows_error_banner(
    client_request,
    mocker,
    mock_s3_upload,
    mock_get_job_doesnt_exist,
    mock_get_users_by_service,
    fake_uuid,
    file_contents,
    expected_error,
    expected_thead,
    expected_tbody,
):
    mock_upload = mocker.patch(
        'app.models.contact_list.s3upload',
        return_value=fake_uuid,
    )
    mock_download = mocker.patch(
        'app.models.contact_list.s3download',
        return_value=file_contents,
    )

    page = client_request.post(
        'main.upload_contact_list',
        service_id=SERVICE_ONE_ID,
        _data={'file': (BytesIO(''.encode('utf-8')), 'invalid.csv')},
        _follow_redirects=True,
    )
    mock_upload.assert_called_once_with(
        SERVICE_ONE_ID,
        {'data': '', 'file_name': 'invalid.csv'},
        ANY,
        bucket='test-contact-list',
    )
    mock_download.assert_called_once_with(
        SERVICE_ONE_ID,
        fake_uuid,
        bucket='test-contact-list',
    )

    assert normalize_spaces(page.select_one('.banner-dangerous').text) == expected_error

    assert page.select_one('form')['action'] == url_for(
        'main.upload_contact_list',
        service_id=SERVICE_ONE_ID,
    )
    assert page.select_one('form input')['type'] == 'file'

    assert normalize_spaces(page.select_one('thead').text) == expected_thead
    assert normalize_spaces(page.select_one('tbody').text) == expected_tbody


def test_upload_csv_file_shows_error_banner_for_too_many_rows(
    client_request,
    mocker,
    mock_s3_upload,
    mock_get_job_doesnt_exist,
    mock_get_users_by_service,
    fake_uuid,
):
    mocker.patch('app.models.contact_list.s3upload', return_value=fake_uuid)
    mocker.patch('app.models.contact_list.s3download', return_value='\n'.join(
        ['phone number'] + (['07700900986'] * 50001)
    ))

    page = client_request.post(
        'main.upload_contact_list',
        service_id=SERVICE_ONE_ID,
        _data={'file': (BytesIO(''.encode('utf-8')), 'invalid.csv')},
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        'Your file has too many rows '
        'Notify can store files up to 50,000 rows in size. '
        'Your file has 50,001 rows. '
        'Skip to file contents'
    )
    assert len(page.select('tbody tr')) == 50
    assert normalize_spaces(page.select_one('.table-show-more-link').text) == (
        'Only showing the first 50 rows'
    )


def test_upload_csv_shows_trial_mode_error(
    client_request,
    mock_get_users_by_service,
    mock_get_job_doesnt_exist,
    fake_uuid,
    mocker
):
    mocker.patch('app.models.contact_list.s3upload', return_value=fake_uuid)
    mocker.patch('app.models.contact_list.s3download', return_value=(
        'phone number\n'
        '07900900321'  # Not in team
    ))

    page = client_request.get(
        'main.check_contact_list',
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        'You cannot save this phone number '
        'In trial mode you can only send to yourself and members of your team '
        'Skip to file contents'
    )
    assert page.select_one('.banner-dangerous a')['href'] == url_for(
        'main.trial_mode_new'
    )


def test_upload_csv_shows_ok_page(
    client_request,
    mock_get_live_service,
    mock_get_users_by_service,
    mock_get_job_doesnt_exist,
    fake_uuid,
    mocker
):
    mocker.patch('app.models.contact_list.s3download', return_value='\n'.join(
        ['email address'] + ['test@example.com'] * 51
    ))
    mock_metadata_set = mocker.patch('app.models.contact_list.set_metadata_on_csv_upload')

    page = client_request.get(
        'main.check_contact_list',
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
        original_file_name='good times.xlsx',
        _test_page_title=False,
    )

    mock_metadata_set.assert_called_once_with(
        SERVICE_ONE_ID,
        fake_uuid,
        bucket='test-contact-list',
        row_count=51,
        original_file_name='good times.xlsx',
        template_type='email',
        valid=True,
    )

    assert normalize_spaces(page.select_one('h1').text) == (
        'good times.xlsx'
    )
    assert normalize_spaces(page.select_one('main p').text) == (
        '51 email addresses found'
    )
    assert page.select_one('form')['action'] == url_for(
        'main.save_contact_list',
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
    )

    assert normalize_spaces(page.select_one('form [type=submit]').text) == (
        'Save contact list'
    )
    assert normalize_spaces(page.select_one('thead').text) == (
        'Row in file 1 email address'
    )
    assert len(page.select('tbody tr')) == 50
    assert normalize_spaces(page.select_one('tbody tr').text) == (
        '2 test@example.com'
    )
    assert normalize_spaces(page.select_one('.table-show-more-link').text) == (
        'Only showing the first 50 rows'
    )


def test_save_contact_list(
    mocker,
    client_request,
    fake_uuid,
    mock_create_contact_list,
):
    mock_get_metadata = mocker.patch('app.models.contact_list.get_csv_metadata', return_value={
        'row_count': 999,
        'valid': True,
        'original_file_name': 'example.csv',
        'template_type': 'email'
    })
    client_request.post(
        'main.save_contact_list',
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.uploads',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )
    mock_get_metadata.assert_called_once_with(
        SERVICE_ONE_ID,
        fake_uuid,
        bucket='test-contact-list',
    )
    mock_create_contact_list.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
        original_file_name='example.csv',
        row_count=999,
        template_type='email',
    )


def test_cant_save_bad_contact_list(
    mocker,
    client_request,
    fake_uuid,
    mock_create_contact_list,
):
    mocker.patch('app.models.contact_list.get_csv_metadata', return_value={
        'row_count': 999,
        'valid': False,
        'original_file_name': 'example.csv',
        'template_type': 'email'
    })
    client_request.post(
        'main.save_contact_list',
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
        _expected_status=403,
    )
    assert mock_create_contact_list.called is False


@freeze_time('2020-03-13 16:51:56')
def test_view_contact_list(
    mocker,
    client_request,
    mock_get_contact_list,
    fake_uuid,
):
    mocker.patch('app.models.contact_list.s3download', return_value='\n'.join(
        ['email address'] + ['test@example.com'] * 51
    ))
    page = client_request.get(
        'main.contact_list',
        service_id=SERVICE_ONE_ID,
        contact_list_id=fake_uuid,
    )
    assert normalize_spaces(page.select_one('h1').text) == (
        'EmergencyContactList.xls'
    )
    assert normalize_spaces(page.select('main p')[0].text) == (
        'Uploaded by Test User today at 10:59am'
    )
    assert normalize_spaces(page.select('main p')[1].text) == (
        'Download this list 51 email addresses'
    )
    assert page.select_one('a[download]')['href'] == url_for(
        'main.download_contact_list',
        service_id=SERVICE_ONE_ID,
        contact_list_id=fake_uuid,
    )
    assert normalize_spaces(page.select_one('table').text).startswith(
        'Email addresses '
        '1 email address '
        '2 test@example.com '
        '3 test@example.com '
    )
    assert normalize_spaces(page.select_one('table').text).endswith(
        '50 test@example.com '
        '51 test@example.com'
    )
    assert normalize_spaces(page.select_one('.table-show-more-link').text) == (
        'Only showing the first 50 rows'
    )


def test_view_contact_list_404s_for_non_existing_list(
    client_request,
    mock_get_no_contact_list,
    fake_uuid,
):
    client_request.get(
        'main.contact_list',
        service_id=SERVICE_ONE_ID,
        contact_list_id=uuid.uuid4(),
        _expected_status=404,
    )


def test_download_contact_list(
    mocker,
    logged_in_client,
    fake_uuid,
    mock_get_contact_list,
):
    mocker.patch(
        'app.models.contact_list.s3download',
        return_value='phone number\n07900900321'
    )
    response = logged_in_client.get(url_for(
        'main.download_contact_list',
        service_id=SERVICE_ONE_ID,
        contact_list_id=fake_uuid,
    ))
    assert response.status_code == 200
    assert response.headers['Content-Type'] == (
        'text/csv; '
        'charset=utf-8'
    )
    assert response.headers['Content-Disposition'] == (
        'attachment; '
        'filename=EmergencyContactList.csv'
    )
    assert response.get_data(as_text=True) == (
        'phone number\n'
        '07900900321'
    )


def test_confirm_delete_contact_list(
    mocker,
    client_request,
    fake_uuid,
    mock_get_contact_list,
):
    mocker.patch(
        'app.models.contact_list.s3download',
        return_value='phone number\n07900900321'
    )
    page = client_request.get(
        'main.delete_contact_list',
        service_id=SERVICE_ONE_ID,
        contact_list_id=fake_uuid,
    )
    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        'Are you sure you want to delete ‘EmergencyContactList.xls’? '
        'Yes, delete'
    )
    assert 'action' not in page.select_one('form')
    assert page.select_one('form')['method'] == 'post'
    assert page.select_one('form button')['type'] == 'submit'


def test_delete_contact_list(
    mocker,
    client_request,
    fake_uuid,
    mock_get_contact_list,
):
    mock_delete = mocker.patch(
        'app.models.contact_list.contact_list_api_client.delete_contact_list'
    )
    client_request.post(
        'main.delete_contact_list',
        service_id=SERVICE_ONE_ID,
        contact_list_id=fake_uuid,
        _expected_redirect=url_for(
            'main.uploads',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )
    mock_delete.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        contact_list_id=fake_uuid,
    )
