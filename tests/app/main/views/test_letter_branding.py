from io import BytesIO

import pytest
from bs4 import BeautifulSoup
from flask import current_app, url_for

from app.main.views.letter_branding import get_png_file_from_svg
from app.s3_client.s3_logo_client import LETTER_TEMP_LOGO_LOCATION


def test_create_letter_branding_does_not_show_branding_info(logged_in_platform_admin_client):
    response = logged_in_platform_admin_client.get(
        url_for('.create_letter_branding')
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.select_one('#logo-img > img') is None
    assert page.select_one('#name').attrs.get('value') == ''
    assert page.select_one('#domain').attrs.get('value') == ''


def test_create_letter_branding_when_uploading_valid_file(
    mocker,
    logged_in_platform_admin_client,
    fake_uuid
):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    filename = 'test.svg'
    expected_temp_filename = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename=filename)

    mock_s3_upload = mocker.patch('app.s3_client.s3_logo_client.utils_s3upload')
    mocker.patch('app.s3_client.s3_logo_client.uuid.uuid4', return_value=fake_uuid)
    mock_delete_temp_files = mocker.patch('app.main.views.letter_branding.delete_letter_temp_file')

    response = logged_in_platform_admin_client.post(
        url_for('.create_letter_branding'),
        data={'file': (BytesIO(''.encode('utf-8')), filename)},
        follow_redirects=True
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.select_one('#logo-img > img').attrs['src'].endswith(expected_temp_filename)
    assert mock_s3_upload.called
    mock_delete_temp_files.assert_not_called()


def test_create_letter_branding_when_uploading_invalid_file(logged_in_platform_admin_client):
    response = logged_in_platform_admin_client.post(
        url_for('.create_letter_branding'),
        data={'file': (BytesIO(''.encode('utf-8')), 'test.png')},
        follow_redirects=True
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.find('h1').text == 'Add letter branding'
    assert page.select_one('.error-message').text.strip() == 'SVG Images only!'


def test_create_letter_branding_deletes_temp_files_when_uploading_a_new_file(
    mocker,
    logged_in_platform_admin_client,
    fake_uuid,
):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename='temp.svg')

    mock_s3_upload = mocker.patch('app.s3_client.s3_logo_client.utils_s3upload')
    mock_delete_temp_files = mocker.patch('app.main.views.letter_branding.delete_letter_temp_file')

    response = logged_in_platform_admin_client.post(
        url_for('.create_letter_branding', logo=temp_logo),
        data={'file': (BytesIO(''.encode('utf-8')), 'new.svg')},
        follow_redirects=True
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert mock_s3_upload.called
    assert mock_delete_temp_files.called
    assert page.find('h1').text == 'Add letter branding'


def test_create_new_letter_branding_shows_preview_of_logo(
    mocker,
    logged_in_platform_admin_client,
    fake_uuid
):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename='temp.svg')

    response = logged_in_platform_admin_client.get(
        url_for('.create_letter_branding', logo=temp_logo)
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.find('h1').text == 'Add letter branding'
    assert page.select_one('#logo-img > img').attrs['src'].endswith(temp_logo)


def test_create_letter_branding_shows_an_error_when_submitting_details_with_no_logo(
    logged_in_platform_admin_client,
    fake_uuid
):
    response = logged_in_platform_admin_client.post(
        url_for('.create_letter_branding'),
        data={
            'name': 'Test brand',
            'domain': 'bl.uk',
            'operation': 'branding-details'
        }
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.find('h1').text == 'Add letter branding'
    assert page.select_one('.error-message').text.strip() == 'You need to upload a file to submit'


@pytest.mark.parametrize('domain', ['bl.uk', ''])
def test_create_letter_branding_persists_logo_when_all_data_is_valid(
    mocker,
    logged_in_platform_admin_client,
    fake_uuid,
    domain
):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename='test.svg')

    mock_letter_client = mocker.patch('app.main.views.letter_branding.letter_branding_client')
    mock_template_preview = mocker.patch(
        'app.main.views.letter_branding.get_png_file_from_svg',
        return_value='fake_png')
    mock_persist_logo = mocker.patch('app.main.views.letter_branding.persist_logo')
    mock_upload_png = mocker.patch('app.main.views.letter_branding.upload_letter_png_logo')
    mock_delete_temp_files = mocker.patch('app.main.views.letter_branding.delete_letter_temp_files_created_by')

    # TODO: remove platform admin page mocks once we no longer redirect there
    mocker.patch('app.main.views.platform_admin.make_columns')
    mocker.patch('app.main.views.platform_admin.platform_stats_api_client.get_aggregate_platform_stats')
    mocker.patch('app.main.views.platform_admin.complaint_api_client.get_complaint_count')

    response = logged_in_platform_admin_client.post(
        url_for('.create_letter_branding', logo=temp_logo),
        data={
            'name': 'Test brand',
            'domain': 'bl.uk',
            'operation': 'branding-details'
        },
        follow_redirects=True
    )

    assert response.status_code == 200

    mock_letter_client.create_letter_branding.assert_called_once_with(
        domain='bl.uk', filename='{}-test'.format(fake_uuid), name='Test brand'
    )
    assert mock_template_preview.called
    mock_persist_logo.assert_called_once_with(
        temp_logo,
        'letters/static/images/letter-template/{}-test.svg'.format(fake_uuid)
    )
    mock_upload_png.assert_called_once_with(
        'letters/static/images/letter-template/{}-test.png'.format(fake_uuid),
        'fake_png',
        current_app.config['AWS_REGION']
    )
    mock_delete_temp_files.assert_called_once_with(user_id)


def test_create_letter_branding_shows_errors_on_name_and_domain_fields(
    logged_in_platform_admin_client,
    fake_uuid
):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename='test.svg')

    response = logged_in_platform_admin_client.post(
        url_for('.create_letter_branding', logo=temp_logo),
        data={
            'name': '',
            'domain': 'example.com',
            'operation': 'branding-details'
        }
    )

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    error_messages = page.find_all('span', class_='error-message')

    assert page.find('h1').text == 'Add letter branding'
    assert len(error_messages) == 2
    assert error_messages[0].text.strip() == 'This field is required.'
    assert error_messages[1].text.strip() == 'Not a known government domain (you might need to update domains.yml)'


def test_get_png_file_from_svg(client, mocker, fake_uuid):
    mocker.patch.dict(
        'flask.current_app.config',
        {'TEMPLATE_PREVIEW_API_HOST': 'localhost', 'TEMPLATE_PREVIEW_API_KEY': 'abc'}
    )
    tp_mock = mocker.patch('app.main.views.letter_branding.requests_get')
    filename = LETTER_TEMP_LOGO_LOCATION.format(user_id=fake_uuid, unique_id=fake_uuid, filename='test.svg')

    get_png_file_from_svg(filename)

    tp_mock.assert_called_once_with(
        'localhost/temp-{}_{}-test.svg.png'.format(fake_uuid, fake_uuid),
        headers={'Authorization': 'Token abc'}
    )
