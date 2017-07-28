from io import BytesIO
from unittest.mock import call

from bs4 import BeautifulSoup
from flask import url_for
import pytest

from app.main.s3_client import TEMP_TAG, LOGO_LOCATION_STRUCTURE

sample_orgs = [
    {'id': '1', 'name': 'org 1', 'colour': 'red', 'logo': 'logo1.png'}, 
    {'id': '2', 'name': 'org 2', 'colour': 'orange', 'logo': 'logo2.png'}, 
    {'id': '3', 'name': None, 'colour': None, 'logo': 'logo3.png'}, 
    {'id': '4', 'name': 'org 4', 'colour': None, 'logo': 'logo4.png'}, 
    {'id': '5', 'name': None, 'colour': 'blue', 'logo': 'logo5.png'}, 
]

@pytest.fixture
def visit_manage_org_with_org(logged_in_platform_admin_client):
    with logged_in_platform_admin_client.session_transaction() as session:
        session['organisation'] = sample_orgs[0]

    response = logged_in_platform_admin_client.get(
        url_for('.manage_org')
    )
    assert response.status_code == 200
    return BeautifulSoup(response.data.decode('utf-8'), 'html.parser')


@pytest.fixture
def visit_manage_org_without_org(logged_in_platform_admin_client):
    response = logged_in_platform_admin_client.get(
        url_for('.manage_org')
    )
    assert response.status_code == 200
    return BeautifulSoup(response.data.decode('utf-8'), 'html.parser')


def test_organisations_page_shows_full_orgs_list(logged_in_platform_admin_client, mocker):
    mocker.patch('app.organisations_client.get_organisations', return_value=sample_orgs)

    response = logged_in_platform_admin_client.get(
        url_for('.organisations')
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert ' '.join(page.find('h1').text.split()) == "Select an organisation to update or create a new organisation"
    for index, label in enumerate(page.select('div.multiple-choice > label')):
        if index < len(sample_orgs):
            if sample_orgs[index]['colour']:
                assert 'background: {};'.format(sample_orgs[index]['colour']) in label.find('span')['style']

            assert ' '.join(label.text.split()) == str(sample_orgs[index]['name'])
            assert label.find('img')['src'].endswith('/' + sample_orgs[index]['logo'])
        else:
            assert ' '.join(label.text.split()) == 'Create a new organisation'


@pytest.mark.parametrize("org_id", [
    'None', '1', '2'
])
def test_organisations_radio_default_to_just_updated_or_new_org(
        logged_in_platform_admin_client, mocker, org_id):
    mocker.patch('app.organisations_client.get_organisations', return_value=sample_orgs)

    response = logged_in_platform_admin_client.get(
        url_for('.organisations', organisation_id=org_id)
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    selected = [r for r in page.select('div.multiple-choice > input') if r.attrs.get('checked')][0]
    assert selected["value"] == org_id


def test_organisations_post_sets_organisation_in_session_after_selecting_org(
        logged_in_platform_admin_client, mocker):
    mocker.patch('app.organisations_client.get_organisations', return_value=sample_orgs)
    response = logged_in_platform_admin_client.post(
        url_for('.organisations'),
        data={'organisation': sample_orgs[0]['id']}
    )
    with logged_in_platform_admin_client.session_transaction() as session:
        assert session['organisation'] == sample_orgs[0]
    assert response.status_code == 302
    assert response.location == url_for('.manage_org', _external=True)


def test_organisations_post_deletes_organisation_session_on_new_org(
        logged_in_platform_admin_client, mocker):
    mocker.patch('app.organisations_client.get_organisations', return_value=sample_orgs)
    with logged_in_platform_admin_client.session_transaction() as session:
        session['organisation'] = sample_orgs[0]

    response = logged_in_platform_admin_client.post(
        url_for('.organisations'),
        data={'organisation': 'None'}
    )

    with logged_in_platform_admin_client.session_transaction() as session:
        assert session.get('organisation') is None
    assert response.status_code == 302
    assert response.location == url_for('.manage_org', _external=True)


def test_manage_orgs_shows_correct_org_info(visit_manage_org_with_org):
    assert visit_manage_org_with_org.select_one('#logo-img > img')['src'].endswith('/' + sample_orgs[0]['logo'])
    assert visit_manage_org_with_org.select_one('#name').attrs.get('value') == sample_orgs[0]['name']
    assert visit_manage_org_with_org.select_one('#colour').attrs.get('value') == sample_orgs[0]['colour']


def test_manage_orgs_does_not_show_data_for_new_org(visit_manage_org_without_org):
    assert visit_manage_org_without_org.select_one('div.page-footer > input.button').has_attr('disabled')
    assert visit_manage_org_without_org.select_one('#logo-img > img') is None
    assert visit_manage_org_without_org.select_one('#name').attrs.get('value') == ''
    assert visit_manage_org_without_org.select_one('#colour').attrs.get('value') == ''


def test_save_is_enabled_when_logo_is_set(visit_manage_org_with_org):
    assert visit_manage_org_with_org.select_one('div.page-footer > input.button').has_attr('disabled') is False


def test_save_is_disabled_when_logo_is_set(visit_manage_org_without_org):
    assert visit_manage_org_without_org.select_one('div.page-footer > input.button').has_attr('disabled')


def test_shows_temp_logo_after_uploading_logo(logged_in_platform_admin_client, mocker, fake_uuid):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_filename = LOGO_LOCATION_STRUCTURE.format(TEMP_TAG.format(user_id), fake_uuid, 'test.png')

    mocker.patch('app.main.views.organisations.upload_logo', return_value=temp_filename)
    mocker.patch('app.main.views.organisations.delete_temp_file')
    mocker.patch('app.main.views.organisations.delete_temp_files_created_by')

    response = logged_in_platform_admin_client.post(
        url_for('.manage_org'),
        data={'file': (BytesIO(''.encode('utf-8')), 'test.png')},
        content_type='multipart/form-data',
        follow_redirects=True
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.select_one('#logo-img > img').attrs['src'].endswith(temp_filename)


def test_save_enabled_after_loading_logo(logged_in_platform_admin_client, mocker, fake_uuid):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_filename = LOGO_LOCATION_STRUCTURE.format(TEMP_TAG.format(user_id), fake_uuid, 'test.png')

    mocker.patch('app.main.views.organisations.upload_logo', return_value=temp_filename)
    mocker.patch('app.main.views.organisations.delete_temp_file')
    mocker.patch('app.main.views.organisations.delete_temp_files_created_by')

    response = logged_in_platform_admin_client.post(
        url_for('.manage_org'),
        data={'file': (BytesIO(''.encode('utf-8')), 'test.png')},
        content_type='multipart/form-data',
        follow_redirects=True
    )

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert not page.select_one('div.page-footer > input.button').has_attr('disabled')


def test_allows_saving_after_uploading_logo():
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_filename = LOGO_LOCATION_STRUCTURE.format(TEMP_TAG.format(user_id), fake_uuid, 'test.png')

    mocker.patch('app.main.views.organisations.upload_logo', return_value=temp_filename)
    mocker.patch('app.main.views.organisations.delete_temp_file')
    mocker.patch('app.main.views.organisations.delete_temp_files_created_by')

    response = logged_in_platform_admin_client.post(
        url_for('.manage_org'),
        data={'file': (BytesIO(''.encode('utf-8')), 'test.png')},
        content_type='multipart/form-data',
        follow_redirects=True
    )

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert not page.select_one('div.page-footer > input.button').has_attr('disabled')


def test_deletes_previous_temp_logo_after_uploading_logo(logged_in_platform_admin_client, mocker, fake_uuid):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_old_filename = LOGO_LOCATION_STRUCTURE.format(TEMP_TAG.format(user_id), fake_uuid, 'old_test.png')
    temp_filename = LOGO_LOCATION_STRUCTURE.format(TEMP_TAG.format(user_id), fake_uuid, 'test.png')

    mocked_upload_logo = mocker.patch(
        'app.main.views.organisations.upload_logo',
        return_value=temp_filename
    )
    mocked_delete_temp_file = mocker.patch('app.main.views.organisations.delete_temp_file')

    logged_in_platform_admin_client.post(
        url_for('.manage_org', logo=temp_old_filename),
        data={'file': (BytesIO(''.encode('utf-8')), 'test.png')},
        content_type='multipart/form-data'
    )

    assert mocked_upload_logo.called
    assert mocked_delete_temp_file.called
    assert mocked_delete_temp_file.call_args == call(temp_old_filename)


def test_logo_persisted_when_organisation_saved(logged_in_platform_admin_client, mocker, fake_uuid):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_filename = LOGO_LOCATION_STRUCTURE.format(TEMP_TAG.format(user_id), fake_uuid, 'test.png')

    mocked_upload_logo = mocker.patch('app.main.views.organisations.upload_logo')
    mocked_persist_logo = mocker.patch('app.main.views.organisations.persist_logo', return_value='test.png')
    mocked_delete_temp_files_by = mocker.patch('app.main.views.organisations.delete_temp_files_created_by')

    logged_in_platform_admin_client.post(
        url_for('.manage_org', logo=temp_filename),
        content_type='multipart/form-data'
    )

    assert not mocked_upload_logo.called
    assert mocked_persist_logo.called
    assert mocked_delete_temp_files_by.called
    assert mocked_delete_temp_files_by.call_args == call(user_id)


def test_shows_colour_when_valid_colour_entered():
    pass