from io import BytesIO
from unittest.mock import call

import pytest
from bs4 import BeautifulSoup
from flask import url_for

from app.main.s3_client import LOGO_LOCATION_STRUCTURE, TEMP_TAG
from tests.conftest import mock_get_email_branding, normalize_spaces


def test_email_branding_page_shows_full_branding_list(
    logged_in_platform_admin_client,
    mock_get_all_email_branding
):

    response = logged_in_platform_admin_client.get(
        url_for('.email_branding')
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(
        page.select_one('h1').text
    ) == "Select an email branding to update or create a new email branding"

    first_label = page.select('div.multiple-choice > label')[0]
    assert 'background: red;' in first_label.find('span')['style']
    assert normalize_spaces(first_label.text) == 'org 1'
    assert first_label.find('img')['src'].endswith('/logo1.png')

    assert normalize_spaces((page.select('div.multiple-choice > label')[-1]).text) == 'Create a new email branding'


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
    assert page.select_one('#colour').attrs.get('value') == ''


def test_create_new_email_branding_without_logo(
    logged_in_platform_admin_client,
    mocker,
    fake_uuid,
    mock_create_email_branding
):
    data = {
        'logo': None,
        'colour': '#ff0000',
        'name': 'new name'
    }

    mock_persist = mocker.patch('app.main.views.email_branding.persist_logo')
    mocker.patch('app.main.views.email_branding.delete_temp_files_created_by')

    logged_in_platform_admin_client.post(
        url_for('.create_email_branding'),
        content_type='multipart/form-data',
        data=data
    )

    assert mock_create_email_branding.called
    assert mock_create_email_branding.call_args == call(
        logo=data['logo'],
        name=data['name'],
        colour=data['colour']
    )
    assert mock_persist.call_args_list == []


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
        'name': 'new name'
    }

    temp_filename = LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id),
        unique_id=fake_uuid,
        filename=data['logo']
    )

    mocker.patch('app.main.views.email_branding.persist_logo', return_value=data['logo'])
    mocker.patch('app.main.views.email_branding.delete_temp_files_created_by')

    logged_in_platform_admin_client.post(
        url_for('.create_email_branding', logo=temp_filename),
        content_type='multipart/form-data',
        data={
            'colour': data['colour'],
            'name': data['name'],
            'cdn_url': 'https://static-logos.cdn.com'
        }
    )

    assert mock_create_email_branding.called
    assert mock_create_email_branding.call_args == call(
        logo=data['logo'],
        name=data['name'],
        colour=data['colour']
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

    temp_old_filename = LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id),
        unique_id=fake_uuid,
        filename='old_test.png'
    )

    temp_filename = LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id),
        unique_id=fake_uuid,
        filename='test.png'
    )

    mocked_upload_logo = mocker.patch(
        'app.main.views.email_branding.upload_logo',
        return_value=temp_filename
    )

    mocked_delete_temp_file = mocker.patch('app.main.views.email_branding.delete_temp_file')

    logged_in_platform_admin_client.post(
        url_for('main.create_email_branding', logo=temp_old_filename, branding_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'test.png')},
        content_type='multipart/form-data'
    )

    assert mocked_upload_logo.called
    assert mocked_delete_temp_file.called
    assert mocked_delete_temp_file.call_args == call(temp_old_filename)


def test_update_exisiting_branding(
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
        'name': 'new name'
    }

    temp_filename = LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id),
        unique_id=fake_uuid,
        filename=data['logo']
    )

    mocker.patch('app.main.views.email_branding.persist_logo', return_value=data['logo'])
    mocker.patch('app.main.views.email_branding.delete_temp_files_created_by')

    logged_in_platform_admin_client.post(
        url_for('.update_email_branding', logo=temp_filename, branding_id=fake_uuid),
        content_type='multipart/form-data',
        data={'colour': data['colour'], 'name': data['name'], 'cdn_url': 'https://static-logos.cdn.com'}
    )

    assert mock_update_email_branding.called
    assert mock_update_email_branding.call_args == call(
        branding_id=fake_uuid,
        logo=data['logo'],
        name=data['name'],
        colour=data['colour']
    )


def test_temp_logo_is_shown_after_uploading_logo(
    logged_in_platform_admin_client,
    mocker,
    fake_uuid,
):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_filename = LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id),
        unique_id=fake_uuid,
        filename='test.png'
    )

    mocker.patch('app.main.views.email_branding.upload_logo', return_value=temp_filename)
    mocker.patch('app.main.views.email_branding.delete_temp_file')

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

    temp_filename = LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id), unique_id=fake_uuid, filename='test.png')

    mocked_upload_logo = mocker.patch('app.main.views.email_branding.upload_logo')
    mocked_persist_logo = mocker.patch('app.main.views.email_branding.persist_logo', return_value='test.png')
    mocked_delete_temp_files_by = mocker.patch('app.main.views.email_branding.delete_temp_files_created_by')

    resp = logged_in_platform_admin_client.post(
        url_for('.create_email_branding', logo=temp_filename),
        content_type='multipart/form-data'
    )

    assert resp.status_code == 302

    assert not mocked_upload_logo.called
    assert mocked_persist_logo.called
    assert mocked_delete_temp_files_by.called
    assert mocked_delete_temp_files_by.call_args == call(user_id)
    assert mock_create_email_branding.called


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
        'name': 'new name'
    }

    mocker.patch('app.main.views.email_branding.delete_temp_files_created_by')

    response = logged_in_platform_admin_client.post(
        url_for('.create_email_branding'),
        content_type='multipart/form-data',
        data=data
    )

    assert response.status_code == expected_status_code
