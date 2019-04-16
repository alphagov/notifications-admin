from io import BytesIO
from unittest.mock import call

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from notifications_python_client.errors import HTTPError

from app.s3_client.s3_logo_client import EMAIL_LOGO_LOCATION_STRUCTURE, TEMP_TAG
from tests.conftest import (
    mock_get_email_branding,
    normalize_spaces,
    platform_admin_user,
)


def test_email_branding_page_shows_full_branding_list(
    logged_in_platform_admin_client,
    mock_get_all_email_branding
):

    response = logged_in_platform_admin_client.get(
        url_for('.email_branding')
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    links = page.select('.message-name a')
    brand_names = [normalize_spaces(link.text) for link in links]
    hrefs = [link['href'] for link in links]

    assert normalize_spaces(
        page.select_one('h1').text
    ) == "Email branding"

    assert page.select_one('.column-three-quarters a')['href'] == url_for('main.create_email_branding')

    assert brand_names == [
        'org 1',
        'org 2',
        'org 3',
        'org 4',
        'org 5',
    ]
    assert hrefs == [
        url_for('.update_email_branding', branding_id=1),
        url_for('.update_email_branding', branding_id=2),
        url_for('.update_email_branding', branding_id=3),
        url_for('.update_email_branding', branding_id=4),
        url_for('.update_email_branding', branding_id=5),
    ]


def test_edit_email_branding_shows_the_correct_branding_info(
    logged_in_platform_admin_client,
    mock_get_email_branding,
    fake_uuid
):
    response = logged_in_platform_admin_client.get(
        url_for('.update_email_branding', branding_id=fake_uuid)
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.select_one('#logo-img > img')['src'].endswith('/example.png')
    assert page.select_one('#name').attrs.get('value') == 'Organisation name'
    assert page.select_one('#text').attrs.get('value') == 'Organisation text'
    assert page.select_one('#colour').attrs.get('value') == '#f00'


def test_create_email_branding_does_not_show_any_branding_info(
    logged_in_platform_admin_client,
    mock_no_email_branding
):

    response = logged_in_platform_admin_client.get(
        url_for('.create_email_branding')
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.select_one('#logo-img > img') is None
    assert page.select_one('#name').attrs.get('value') == ''
    assert page.select_one('#text').attrs.get('value') == ''
    assert page.select_one('#colour').attrs.get('value') == ''


def test_create_new_email_branding_without_logo(
    logged_in_platform_admin_client,
    mocker,
    fake_uuid,
    mock_create_email_branding,
):
    data = {
        'logo': None,
        'colour': '#ff0000',
        'text': 'new text',
        'name': 'new name',
        'brand_type': 'org'
    }

    mock_persist = mocker.patch('app.main.views.email_branding.persist_logo')
    mocker.patch('app.main.views.email_branding.delete_email_temp_files_created_by')

    logged_in_platform_admin_client.post(
        url_for('.create_email_branding'),
        content_type='multipart/form-data',
        data=data
    )

    assert mock_create_email_branding.called
    assert mock_create_email_branding.call_args == call(
        logo=data['logo'],
        name=data['name'],
        text=data['text'],
        colour=data['colour'],
        brand_type=data['brand_type']
    )
    assert mock_persist.call_args_list == []


def test_create_email_branding_requires_a_name_when_submitting_logo_details(
    client_request,
    mocker,
    fake_uuid,
    mock_create_email_branding,
):
    mocker.patch('app.main.views.email_branding.persist_logo')
    mocker.patch('app.main.views.email_branding.delete_email_temp_files_created_by')
    data = {
        'operation': 'email-branding-details',
        'logo': '',
        'colour': '#ff0000',
        'text': 'new text',
        'name': '',
        'brand_type': 'org',
    }
    client_request.login(platform_admin_user(fake_uuid))
    page = client_request.post(
        '.create_email_branding',
        content_type='multipart/form-data',
        _data=data,
        _expected_status=200,
    )

    assert page.select_one('.error-message').text.strip() == 'This field is required'
    assert mock_create_email_branding.called is False


def test_create_email_branding_does_not_require_a_name_when_uploading_a_file(
    client_request,
    mocker,
    fake_uuid,
):
    mocker.patch('app.main.views.email_branding.upload_email_logo', return_value='temp_filename')
    data = {
        'file': (BytesIO(''.encode('utf-8')), 'test.png'),
        'colour': '',
        'text': '',
        'name': '',
        'brand_type': 'org',
    }
    client_request.login(platform_admin_user(fake_uuid))
    page = client_request.post(
        '.create_email_branding',
        content_type='multipart/form-data',
        _data=data,
        _follow_redirects=True
    )

    assert not page.find('.error-message')


def test_create_new_email_branding_when_branding_saved(
    logged_in_platform_admin_client,
    mocker,
    mock_create_email_branding,
    fake_uuid
):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    data = {
        'logo': 'test.png',
        'colour': '#ff0000',
        'text': 'new text',
        'name': 'new name',
        'brand_type': 'org_banner'
    }

    temp_filename = EMAIL_LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id),
        unique_id=fake_uuid,
        filename=data['logo']
    )

    mocker.patch('app.main.views.email_branding.persist_logo')
    mocker.patch('app.main.views.email_branding.delete_email_temp_files_created_by')

    logged_in_platform_admin_client.post(
        url_for('.create_email_branding', logo=temp_filename),
        content_type='multipart/form-data',
        data={
            'colour': data['colour'],
            'name': data['name'],
            'text': data['text'],
            'cdn_url': 'https://static-logos.cdn.com',
            'brand_type': data['brand_type']
        }
    )

    updated_logo_name = '{}-{}'.format(fake_uuid, data['logo'])

    assert mock_create_email_branding.called
    assert mock_create_email_branding.call_args == call(
        logo=updated_logo_name,
        name=data['name'],
        text=data['text'],
        colour=data['colour'],
        brand_type=data['brand_type']
    )


@pytest.mark.parametrize('endpoint, has_data', [
    ('main.create_email_branding', False),
    ('main.update_email_branding', True),
])
def test_deletes_previous_temp_logo_after_uploading_logo(
    logged_in_platform_admin_client,
    mocker,
    endpoint,
    has_data,
    fake_uuid
):
    if has_data:
        mock_get_email_branding(mocker, fake_uuid)

    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_old_filename = EMAIL_LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id),
        unique_id=fake_uuid,
        filename='old_test.png'
    )

    temp_filename = EMAIL_LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id),
        unique_id=fake_uuid,
        filename='test.png'
    )

    mocked_upload_email_logo = mocker.patch(
        'app.main.views.email_branding.upload_email_logo',
        return_value=temp_filename
    )

    mocked_delete_email_temp_file = mocker.patch('app.main.views.email_branding.delete_email_temp_file')

    logged_in_platform_admin_client.post(
        url_for('main.create_email_branding', logo=temp_old_filename, branding_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'test.png')},
        content_type='multipart/form-data'
    )

    assert mocked_upload_email_logo.called
    assert mocked_delete_email_temp_file.called
    assert mocked_delete_email_temp_file.call_args == call(temp_old_filename)


def test_update_existing_branding(
    logged_in_platform_admin_client,
    mocker,
    fake_uuid,
    mock_get_email_branding,
    mock_update_email_branding
):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    data = {
        'logo': 'test.png',
        'colour': '#0000ff',
        'text': 'new text',
        'name': 'new name',
        'brand_type': 'both'
    }

    temp_filename = EMAIL_LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id),
        unique_id=fake_uuid,
        filename=data['logo']
    )

    mocker.patch('app.main.views.email_branding.persist_logo')
    mocker.patch('app.main.views.email_branding.delete_email_temp_files_created_by')

    logged_in_platform_admin_client.post(
        url_for('.update_email_branding', logo=temp_filename, branding_id=fake_uuid),
        content_type='multipart/form-data',
        data={'colour': data['colour'], 'name': data['name'], 'text': data['text'],
              'cdn_url': 'https://static-logos.cdn.com',
              'brand_type': data['brand_type']
              }
    )

    updated_logo_name = '{}-{}'.format(fake_uuid, data['logo'])

    assert mock_update_email_branding.called
    assert mock_update_email_branding.call_args == call(
        branding_id=fake_uuid,
        logo=updated_logo_name,
        name=data['name'],
        text=data['text'],
        colour=data['colour'],
        brand_type=data['brand_type']
    )


def test_temp_logo_is_shown_after_uploading_logo(
    logged_in_platform_admin_client,
    mocker,
    fake_uuid,
):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_filename = EMAIL_LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id),
        unique_id=fake_uuid,
        filename='test.png'
    )

    mocker.patch('app.main.views.email_branding.upload_email_logo', return_value=temp_filename)
    mocker.patch('app.main.views.email_branding.delete_email_temp_file')

    response = logged_in_platform_admin_client.post(
        url_for('main.create_email_branding'),
        data={'file': (BytesIO(''.encode('utf-8')), 'test.png')},
        content_type='multipart/form-data',
        follow_redirects=True
    )

    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.select_one('#logo-img > img').attrs['src'].endswith(temp_filename)


def test_logo_persisted_when_organisation_saved(
    logged_in_platform_admin_client,
    mock_create_email_branding,
    mocker,
    fake_uuid
):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_filename = EMAIL_LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id), unique_id=fake_uuid, filename='test.png')

    mocked_upload_email_logo = mocker.patch('app.main.views.email_branding.upload_email_logo')
    mocked_persist_logo = mocker.patch('app.main.views.email_branding.persist_logo')
    mocked_delete_email_temp_files_by = mocker.patch('app.main.views.email_branding.delete_email_temp_files_created_by')

    resp = logged_in_platform_admin_client.post(
        url_for('.create_email_branding', logo=temp_filename),
        content_type='multipart/form-data'
    )
    assert resp.status_code == 302

    assert not mocked_upload_email_logo.called
    assert mocked_persist_logo.called
    assert mocked_delete_email_temp_files_by.called
    assert mocked_delete_email_temp_files_by.call_args == call(user_id)
    assert mock_create_email_branding.called


def test_logo_does_not_get_persisted_if_updating_email_branding_client_throws_an_error(
    logged_in_platform_admin_client,
    mock_create_email_branding,
    mocker,
    fake_uuid
):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_filename = EMAIL_LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id), unique_id=fake_uuid, filename='test.png')

    mocked_persist_logo = mocker.patch('app.main.views.email_branding.persist_logo')
    mocked_delete_email_temp_files_by = mocker.patch('app.main.views.email_branding.delete_email_temp_files_created_by')
    mocker.patch('app.main.views.email_branding.email_branding_client.create_email_branding', side_effect=HTTPError())

    logged_in_platform_admin_client.post(
        url_for('.create_email_branding', logo=temp_filename),
        content_type='multipart/form-data'
    )

    assert not mocked_persist_logo.called
    assert not mocked_delete_email_temp_files_by.called


@pytest.mark.parametrize('colour_hex, expected_status_code', [
    ('#FF00FF', 302),
    ('hello', 200),
    ('', 302),
])
def test_colour_regex_validation(
    logged_in_platform_admin_client,
    mocker,
    fake_uuid,
    colour_hex,
    expected_status_code,
    mock_create_email_branding
):
    data = {
        'logo': None,
        'colour': colour_hex,
        'text': 'new text',
        'name': 'new name',
        'brand_type': 'org'
    }

    mocker.patch('app.main.views.email_branding.delete_email_temp_files_created_by')

    response = logged_in_platform_admin_client.post(
        url_for('.create_email_branding'),
        content_type='multipart/form-data',
        data=data
    )
    assert response.status_code == expected_status_code
