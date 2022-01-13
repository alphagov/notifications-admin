from io import BytesIO
from unittest.mock import Mock, call
from uuid import UUID

import pytest
from botocore.exceptions import ClientError as BotoClientError
from flask import url_for
from notifications_python_client.errors import HTTPError

from app.s3_client.s3_logo_client import (
    LETTER_TEMP_LOGO_LOCATION,
    permanent_letter_logo_name,
)
from tests.conftest import normalize_spaces


def test_letter_branding_page_shows_full_branding_list(
    client_request,
    platform_admin_user,
    mock_get_all_letter_branding
):
    client_request.login(platform_admin_user)
    page = client_request.get('.letter_branding')

    links = page.select('.message-name a')
    brand_names = [normalize_spaces(link.text) for link in links]
    hrefs = [link['href'] for link in links]

    assert normalize_spaces(
        page.select_one('h1').text
    ) == "Letter branding"

    assert page.select('.govuk-grid-column-three-quarters a')[-1]['href'] == url_for('main.create_letter_branding')

    assert brand_names == [
        'HM Government',
        'Land Registry',
        'Animal and Plant Health Agency',
    ]

    assert hrefs == [
        url_for('.update_letter_branding', branding_id=str(UUID(int=0))),
        url_for('.update_letter_branding', branding_id=str(UUID(int=1))),
        url_for('.update_letter_branding', branding_id=str(UUID(int=2))),
    ]


def test_update_letter_branding_shows_the_current_letter_brand(
    client_request,
    platform_admin_user,
    mock_get_letter_branding_by_id,
    fake_uuid,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        '.update_letter_branding',
        branding_id=fake_uuid,
    )

    assert page.find('h1').text == 'Update letter branding'
    assert page.select_one('#logo-img > img')['src'].endswith('/hm-government.svg')
    assert page.select_one('#name').attrs.get('value') == 'HM Government'
    assert page.select_one('#file').attrs.get('accept') == '.svg'


def test_update_letter_branding_with_new_valid_file(
    mocker,
    client_request,
    platform_admin_user,
    mock_get_letter_branding_by_id,
    fake_uuid
):
    with client_request.session_transaction() as session:
        user_id = session["user_id"]

    filename = 'new_file.svg'
    expected_temp_filename = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename=filename)

    mock_s3_upload = mocker.patch('app.s3_client.s3_logo_client.utils_s3upload')
    mocker.patch('app.s3_client.s3_logo_client.uuid.uuid4', return_value=fake_uuid)
    mock_delete_temp_files = mocker.patch('app.main.views.letter_branding.delete_letter_temp_file')

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.update_letter_branding',
        branding_id=fake_uuid,
        _data={'file': (BytesIO(''.encode('utf-8')), filename)},
        _follow_redirects=True,
    )

    assert page.select_one('#logo-img > img')['src'].endswith(expected_temp_filename)
    assert page.select_one('#name').attrs.get('value') == 'HM Government'

    assert mock_s3_upload.called
    assert mock_delete_temp_files.called is False


def test_update_letter_branding_when_uploading_invalid_file(
    client_request,
    platform_admin_user,
    mock_get_letter_branding_by_id,
    fake_uuid,
):
    client_request.login(platform_admin_user)
    page = client_request.post(
        '.update_letter_branding',
        branding_id=fake_uuid,
        _data={'file': (BytesIO(''.encode('utf-8')), 'test.png')},
        _follow_redirects=True
    )

    assert page.find('h1').text == 'Update letter branding'
    assert page.select_one('.error-message').text.strip() == 'SVG Images only!'


def test_update_letter_branding_deletes_any_temp_files_when_uploading_a_file(
    mocker,
    client_request,
    platform_admin_user,
    mock_get_letter_branding_by_id,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        user_id = session["user_id"]

    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename='temp.svg')

    mock_s3_upload = mocker.patch('app.s3_client.s3_logo_client.utils_s3upload')
    mock_delete_temp_files = mocker.patch('app.main.views.letter_branding.delete_letter_temp_file')

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.update_letter_branding',
        branding_id=fake_uuid,
        logo=temp_logo,
        _data={'file': (BytesIO(''.encode('utf-8')), 'new_uploaded_file.svg')},
        _follow_redirects=True,
    )

    assert mock_s3_upload.called
    assert mock_delete_temp_files.called
    assert page.find('h1').text == 'Update letter branding'


def test_update_letter_branding_with_original_file_and_new_details(
    mocker,
    client_request,
    platform_admin_user,
    mock_get_all_letter_branding,
    mock_get_letter_branding_by_id,
    fake_uuid
):
    mock_client_update = mocker.patch('app.main.views.letter_branding.letter_branding_client.update_letter_branding')
    mock_upload_logos = mocker.patch('app.main.views.letter_branding.upload_letter_svg_logo')

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.update_letter_branding',
        branding_id=fake_uuid,
        _data={
            'name': 'Updated name',
            'operation': 'branding-details'
        },
        _follow_redirects=True,
    )

    assert page.find('h1').text == 'Letter branding'
    assert mock_upload_logos.called is False

    mock_client_update.assert_called_once_with(
        branding_id=fake_uuid,
        filename='hm-government',
        name='Updated name'
    )


def test_update_letter_branding_shows_form_errors_on_name_fields(
    mocker,
    client_request,
    platform_admin_user,
    mock_get_letter_branding_by_id,
    fake_uuid
):
    mocker.patch('app.main.views.letter_branding.letter_branding_client.update_letter_branding')

    logo = permanent_letter_logo_name('hm-government', 'svg')

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.update_letter_branding',
        branding_id=fake_uuid,
        logo=logo,
        _data={
            'name': '',
            'operation': 'branding-details'
        },
        _follow_redirects=True
    )

    error_messages = page.find_all('span', class_='govuk-error-message')

    assert page.find('h1').text == 'Update letter branding'
    assert len(error_messages) == 1
    assert 'This field is required.' in error_messages[0].text.strip()


def test_update_letter_branding_shows_database_errors_on_name_field(
    mocker,
    client_request,
    platform_admin_user,
    mock_get_letter_branding_by_id,
    fake_uuid,
):
    mocker.patch('app.main.views.letter_branding.letter_branding_client.update_letter_branding', side_effect=HTTPError(
        response=Mock(
            status_code=400,
            json={
                'result': 'error',
                'message': {
                    'name': {
                        'name already in use'
                    }
                }
            }
        ),
        message={'name': ['name already in use']}
    ))

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.update_letter_branding',
        branding_id=fake_uuid,
        _data={
            'name': 'my brand',
            'operation': 'branding-details'
        },
        _expected_status=200,
    )

    error_message = page.find('span', class_='govuk-error-message').text.strip()

    assert page.find('h1').text == 'Update letter branding'
    assert 'name already in use' in error_message


def test_update_letter_branding_with_new_file_and_new_details(
    mocker,
    client_request,
    platform_admin_user,
    mock_get_all_letter_branding,
    mock_get_letter_branding_by_id,
    fake_uuid
):
    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=fake_uuid, unique_id=fake_uuid, filename='new_file.svg')

    mock_client_update = mocker.patch('app.main.views.letter_branding.letter_branding_client.update_letter_branding')
    mock_persist_logo = mocker.patch('app.main.views.letter_branding.persist_logo')
    mock_delete_temp_files = mocker.patch('app.main.views.letter_branding.delete_letter_temp_files_created_by')

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.update_letter_branding',
        branding_id=fake_uuid,
        logo=temp_logo,
        _data={
            'name': 'Updated name',
            'operation': 'branding-details'
        },
        _follow_redirects=True
    )
    assert page.find('h1').text == 'Letter branding'

    mock_client_update.assert_called_once_with(
        branding_id=fake_uuid,
        filename='{}-new_file'.format(fake_uuid),
        name='Updated name'
    )
    mock_persist_logo.assert_called_once_with(
        temp_logo,
        'letters/static/images/letter-template/{}-new_file.svg'.format(fake_uuid)
    )
    mock_delete_temp_files.assert_called_once_with(fake_uuid)


def test_update_letter_branding_rolls_back_db_changes_and_shows_error_if_saving_to_s3_fails(
    mocker,
    client_request,
    platform_admin_user,
    mock_get_letter_branding_by_id,
    fake_uuid
):
    mock_client_update = mocker.patch('app.main.views.letter_branding.letter_branding_client.update_letter_branding')
    mocker.patch('app.main.views.letter_branding.upload_letter_svg_logo', side_effect=BotoClientError({}, 'error'))

    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=fake_uuid, unique_id=fake_uuid, filename='new_file.svg')
    client_request.login(platform_admin_user)
    page = client_request.post(
        '.update_letter_branding',
        branding_id=fake_uuid,
        logo=temp_logo,
        _data={
            'name': 'Updated name',
            'operation': 'branding-details'
        },
        _follow_redirects=True,
    )
    assert page.find('h1').text == 'Update letter branding'
    assert page.select_one('.error-message').text.strip() == 'Error saving uploaded file - try uploading again'

    assert mock_client_update.call_count == 2
    assert mock_client_update.call_args_list == [
        call(branding_id=fake_uuid, filename='{}-new_file'.format(fake_uuid), name='Updated name'),
        call(branding_id=fake_uuid, filename='hm-government', name='HM Government')
    ]


def test_create_letter_branding_does_not_show_branding_info(
    client_request,
    platform_admin_user,
):
    client_request.login(platform_admin_user)
    page = client_request.get('.create_letter_branding')

    assert page.select_one('#logo-img > img') is None
    assert page.select_one('#name').attrs.get('value') is None
    assert page.select_one('#file').attrs.get('accept') == '.svg'


def test_create_letter_branding_when_uploading_valid_file(
    mocker,
    client_request,
    platform_admin_user,
    fake_uuid
):
    with client_request.session_transaction() as session:
        user_id = session["user_id"]

    filename = 'test.svg'
    expected_temp_filename = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename=filename)

    mock_s3_upload = mocker.patch('app.s3_client.s3_logo_client.utils_s3upload')
    mocker.patch('app.s3_client.s3_logo_client.uuid.uuid4', return_value=fake_uuid)
    mock_delete_temp_files = mocker.patch('app.main.views.letter_branding.delete_letter_temp_file')

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.create_letter_branding',
        _data={'file': (BytesIO("""
            <svg height="100" width="100">
            <circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" /></svg>
        """.encode('utf-8')), filename)},
        _follow_redirects=True,
    )

    assert page.select_one('#logo-img > img').attrs['src'].endswith(expected_temp_filename)
    assert mock_s3_upload.called
    assert mock_delete_temp_files.called is False


@pytest.mark.parametrize('svg_contents, expected_error', (
    (
        '''
            <svg height="100" width="100">
            <image href="someurlgoeshere" x="0" y="0" height="100" width="100"></image></svg>
        ''',
        'This SVG has an embedded raster image in it and will not render well',
    ),
    (
        '''
            <svg height="100" width="100">
                <text>Will render differently depending on fonts installed</text>
            </svg>
        ''',
        'This SVG has text which has not been converted to paths and may not render well',
    ),
))
def test_create_letter_branding_fails_validation_when_uploading_SVG_with_bad_element(
    mocker,
    client_request,
    platform_admin_user,
    fake_uuid,
    svg_contents,
    expected_error,
):
    filename = 'test.svg'

    mock_s3_upload = mocker.patch('app.s3_client.s3_logo_client.utils_s3upload')

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.create_letter_branding',
        _data={'file': (BytesIO(svg_contents.encode('utf-8')), filename)},
        _follow_redirects=True,
    )

    assert normalize_spaces(page.find('h1').text) == "Add letter branding"
    assert normalize_spaces(page.select_one(".error-message").text) == expected_error

    assert page.findAll('div', {'id': 'logo-img'}) == []

    assert mock_s3_upload.called is False


def test_create_letter_branding_when_uploading_invalid_file(
    client_request,
    platform_admin_user,
):
    client_request.login(platform_admin_user)
    page = client_request.post(
        '.create_letter_branding',
        _data={'file': (BytesIO(''.encode('utf-8')), 'test.png')},
        _follow_redirects=True,
    )
    assert page.find('h1').text == 'Add letter branding'
    assert page.select_one('.error-message').text.strip() == 'SVG Images only!'


def test_create_letter_branding_deletes_temp_files_when_uploading_a_new_file(
    mocker,
    client_request,
    platform_admin_user,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        user_id = session["user_id"]

    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename='temp.svg')

    mock_s3_upload = mocker.patch('app.s3_client.s3_logo_client.utils_s3upload')
    mock_delete_temp_files = mocker.patch('app.main.views.letter_branding.delete_letter_temp_file')

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.create_letter_branding',
        logo=temp_logo,
        _data={'file': (BytesIO(''.encode('utf-8')), 'new.svg')},
        _follow_redirects=True
    )
    assert mock_s3_upload.called
    assert mock_delete_temp_files.called
    assert page.find('h1').text == 'Add letter branding'


def test_create_new_letter_branding_shows_preview_of_logo(
    mocker,
    client_request,
    platform_admin_user,
    fake_uuid
):
    with client_request.session_transaction() as session:
        user_id = session["user_id"]

    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename='temp.svg')

    client_request.login(platform_admin_user)
    page = client_request.get(
        '.create_letter_branding',
        logo=temp_logo,
    )

    assert page.find('h1').text == 'Add letter branding'
    assert page.select_one('#logo-img > img').attrs['src'].endswith(temp_logo)


def test_create_letter_branding_shows_an_error_when_submitting_details_with_no_logo(
    client_request,
    platform_admin_user,
    fake_uuid
):
    client_request.login(platform_admin_user)
    page = client_request.post(
        '.create_letter_branding',
        _data={
            'name': 'Test brand',
            'operation': 'branding-details'
        },
        _expected_status=200,
    )

    assert page.find('h1').text == 'Add letter branding'
    assert page.select_one('.error-message').text.strip() == 'You need to upload a file to submit'


def test_create_letter_branding_persists_logo_when_all_data_is_valid(
    mocker,
    client_request,
    platform_admin_user,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        user_id = session["user_id"]

    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename='test.svg')

    mock_letter_client = mocker.patch('app.main.views.letter_branding.letter_branding_client')
    mock_persist_logo = mocker.patch('app.main.views.letter_branding.persist_logo')
    mock_delete_temp_files = mocker.patch('app.main.views.letter_branding.delete_letter_temp_files_created_by')

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.create_letter_branding',
        logo=temp_logo,
        _data={
            'name': 'Test brand',
            'operation': 'branding-details'
        },
        _follow_redirects=True
    )

    assert page.find('h1').text == 'Letter branding'

    mock_letter_client.create_letter_branding.assert_called_once_with(
        filename='{}-test'.format(fake_uuid), name='Test brand'
    )
    mock_persist_logo.assert_called_once_with(
        temp_logo,
        'letters/static/images/letter-template/{}-test.svg'.format(fake_uuid)
    )
    mock_delete_temp_files.assert_called_once_with(user_id)


def test_create_letter_branding_shows_form_errors_on_name_field(
    client_request,
    platform_admin_user,
    fake_uuid
):
    with client_request.session_transaction() as session:
        user_id = session["user_id"]

    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename='test.svg')

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.create_letter_branding',
        logo=temp_logo,
        _data={
            'name': '',
            'operation': 'branding-details'
        },
        _expected_status=200,
    )

    error_messages = page.find_all('span', class_='govuk-error-message')

    assert page.find('h1').text == 'Add letter branding'
    assert len(error_messages) == 1
    assert 'This field is required.' in error_messages[0].text.strip()


def test_create_letter_branding_shows_database_errors_on_name_fields(
    mocker,
    client_request,
    platform_admin_user,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        user_id = session["user_id"]

    mocker.patch('app.main.views.letter_branding.letter_branding_client.create_letter_branding', side_effect=HTTPError(
        response=Mock(
            status_code=400,
            json={
                'result': 'error',
                'message': {
                    'name': {
                        'name already in use'
                    }
                }
            }
        ),
        message={'name': ['name already in use']}
    ))

    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename='test.svg')

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.create_letter_branding',
        logo=temp_logo,
        _data={
            'name': 'my brand',
            'operation': 'branding-details'
        },
        _expected_status=200,
    )

    error_message = page.find('span', class_='govuk-error-message').text.strip()

    assert page.find('h1').text == 'Add letter branding'
    assert 'name already in use' in error_message
