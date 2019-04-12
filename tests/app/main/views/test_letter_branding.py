from io import BytesIO
from unittest.mock import Mock, call
from uuid import UUID

from botocore.exceptions import ClientError as BotoClientError
from bs4 import BeautifulSoup
from flask import current_app, url_for
from notifications_python_client.errors import HTTPError

from app.main.views.letter_branding import get_png_file_from_svg
from app.s3_client.s3_logo_client import (
    LETTER_TEMP_LOGO_LOCATION,
    permanent_letter_logo_name,
)
from tests.conftest import normalize_spaces


def test_letter_branding_page_shows_full_branding_list(
    logged_in_platform_admin_client,
    mock_get_all_letter_branding
):
    response = logged_in_platform_admin_client.get(
        url_for('.letter_branding')
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    links = page.select('.message-name a')
    brand_names = [normalize_spaces(link.text) for link in links]
    hrefs = [link['href'] for link in links]

    assert normalize_spaces(
        page.select_one('h1').text
    ) == "Letter branding"

    assert page.select_one('.column-three-quarters a')['href'] == url_for('main.create_letter_branding')

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
    logged_in_platform_admin_client,
    mock_get_letter_branding_by_id,
):
    response = logged_in_platform_admin_client.get(
        url_for('.update_letter_branding', branding_id='abc')
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.find('h1').text == 'Update letter branding'
    assert page.select_one('#logo-img > img')['src'].endswith('/hm-government.svg')
    assert page.select_one('#name').attrs.get('value') == 'HM Government'


def test_update_letter_branding_with_new_valid_file(
    mocker,
    logged_in_platform_admin_client,
    mock_get_letter_branding_by_id,
    fake_uuid
):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    filename = 'new_file.svg'
    expected_temp_filename = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename=filename)

    mock_s3_upload = mocker.patch('app.s3_client.s3_logo_client.utils_s3upload')
    mocker.patch('app.s3_client.s3_logo_client.uuid.uuid4', return_value=fake_uuid)
    mock_delete_temp_files = mocker.patch('app.main.views.letter_branding.delete_letter_temp_file')

    response = logged_in_platform_admin_client.post(
        url_for('.update_letter_branding', branding_id='abc'),
        data={'file': (BytesIO(''.encode('utf-8')), filename)},
        follow_redirects=True
    )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.select_one('#logo-img > img')['src'].endswith(expected_temp_filename)
    assert page.select_one('#name').attrs.get('value') == 'HM Government'

    assert mock_s3_upload.called
    mock_delete_temp_files.assert_not_called()


def test_update_letter_branding_when_uploading_invalid_file(
    logged_in_platform_admin_client,
    mock_get_letter_branding_by_id
):
    response = logged_in_platform_admin_client.post(
        url_for('.update_letter_branding', branding_id='abc'),
        data={'file': (BytesIO(''.encode('utf-8')), 'test.png')},
        follow_redirects=True
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.find('h1').text == 'Update letter branding'
    assert page.select_one('.error-message').text.strip() == 'SVG Images only!'


def test_update_letter_branding_deletes_any_temp_files_when_uploading_a_file(
    mocker,
    logged_in_platform_admin_client,
    mock_get_letter_branding_by_id,
    fake_uuid,
):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=fake_uuid, filename='temp.svg')

    mock_s3_upload = mocker.patch('app.s3_client.s3_logo_client.utils_s3upload')
    mock_delete_temp_files = mocker.patch('app.main.views.letter_branding.delete_letter_temp_file')

    response = logged_in_platform_admin_client.post(
        url_for('.update_letter_branding', branding_id='abc', logo=temp_logo),
        data={'file': (BytesIO(''.encode('utf-8')), 'new_uploaded_file.svg')},
        follow_redirects=True
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert mock_s3_upload.called
    assert mock_delete_temp_files.called
    assert page.find('h1').text == 'Update letter branding'


def test_update_letter_branding_with_original_file_and_new_details(
    mocker,
    logged_in_platform_admin_client,
    mock_get_all_letter_branding,
    mock_get_letter_branding_by_id,
    fake_uuid
):
    mock_client_update = mocker.patch('app.main.views.letter_branding.letter_branding_client.update_letter_branding')
    mock_template_preview = mocker.patch('app.main.views.letter_branding.get_png_file_from_svg')
    mock_upload_logos = mocker.patch('app.main.views.letter_branding.upload_letter_logos')

    response = logged_in_platform_admin_client.post(
        url_for('.update_letter_branding', branding_id=fake_uuid),
        data={
            'name': 'Updated name',
            'operation': 'branding-details'
        },
        follow_redirects=True
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert response.status_code == 200
    assert page.find('h1').text == 'Letter branding'

    mock_upload_logos.assert_not_called()
    mock_template_preview.assert_not_called()

    mock_client_update.assert_called_once_with(
        branding_id=fake_uuid,
        filename='hm-government',
        name='Updated name'
    )


def test_update_letter_branding_shows_form_errors_on_name_fields(
    mocker,
    logged_in_platform_admin_client,
    mock_get_letter_branding_by_id,
    fake_uuid
):
    mocker.patch('app.main.views.letter_branding.letter_branding_client.update_letter_branding')

    logo = permanent_letter_logo_name('hm-government', 'svg')

    response = logged_in_platform_admin_client.post(
        url_for('.update_letter_branding', branding_id=fake_uuid, logo=logo),
        data={
            'name': '',
            'operation': 'branding-details'
        },
        follow_redirects=True
    )

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    error_messages = page.find_all('span', class_='error-message')

    assert page.find('h1').text == 'Update letter branding'
    assert len(error_messages) == 1
    assert error_messages[0].text.strip() == 'This field is required.'


def test_update_letter_branding_shows_database_errors_on_name_field(
    mocker,
    logged_in_platform_admin_client,
    mock_get_letter_branding_by_id,
    fake_uuid,
):
    mocker.patch('app.main.views.letter_branding.get_png_file_from_svg')
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

    response = logged_in_platform_admin_client.post(
        url_for('.update_letter_branding', branding_id='abc'),
        data={
            'name': 'my brand',
            'operation': 'branding-details'
        }
    )

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    error_message = page.find('span', class_='error-message').text.strip()

    assert page.find('h1').text == 'Update letter branding'
    assert error_message == 'name already in use'


def test_update_letter_branding_with_new_file_and_new_details(
    mocker,
    logged_in_platform_admin_client,
    mock_get_all_letter_branding,
    mock_get_letter_branding_by_id,
    fake_uuid
):
    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=fake_uuid, unique_id=fake_uuid, filename='new_file.svg')

    mock_client_update = mocker.patch('app.main.views.letter_branding.letter_branding_client.update_letter_branding')
    mock_template_preview = mocker.patch(
        'app.main.views.letter_branding.get_png_file_from_svg',
        return_value='fake_png')
    mock_persist_logo = mocker.patch('app.main.views.letter_branding.persist_logo')
    mock_upload_png = mocker.patch('app.main.views.letter_branding.upload_letter_png_logo')
    mock_delete_temp_files = mocker.patch('app.main.views.letter_branding.delete_letter_temp_files_created_by')

    response = logged_in_platform_admin_client.post(
        url_for('.update_letter_branding', branding_id=fake_uuid, logo=temp_logo),
        data={
            'name': 'Updated name',
            'operation': 'branding-details'
        },
        follow_redirects=True
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert response.status_code == 200
    assert page.find('h1').text == 'Letter branding'

    assert mock_template_preview.called
    mock_client_update.assert_called_once_with(
        branding_id=fake_uuid,
        filename='{}-new_file'.format(fake_uuid),
        name='Updated name'
    )
    mock_persist_logo.assert_called_once_with(
        temp_logo,
        'letters/static/images/letter-template/{}-new_file.svg'.format(fake_uuid)
    )
    mock_upload_png.assert_called_once_with(
        'letters/static/images/letter-template/{}-new_file.png'.format(fake_uuid),
        'fake_png',
        current_app.config['AWS_REGION']
    )
    mock_delete_temp_files.assert_called_once_with(fake_uuid)


def test_update_letter_branding_rolls_back_db_changes_and_shows_error_if_saving_to_s3_fails(
    mocker,
    logged_in_platform_admin_client,
    mock_get_letter_branding_by_id,
    fake_uuid
):
    mocker.patch('app.main.views.letter_branding.get_png_file_from_svg',)
    mock_client_update = mocker.patch('app.main.views.letter_branding.letter_branding_client.update_letter_branding')
    mocker.patch('app.main.views.letter_branding.upload_letter_logos', side_effect=BotoClientError({}, 'error'))

    temp_logo = LETTER_TEMP_LOGO_LOCATION.format(user_id=fake_uuid, unique_id=fake_uuid, filename='new_file.svg')
    response = logged_in_platform_admin_client.post(
        url_for('.update_letter_branding', branding_id=fake_uuid, logo=temp_logo),
        data={
            'name': 'Updated name',
            'operation': 'branding-details'
        },
        follow_redirects=True
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert response.status_code == 200
    assert page.find('h1').text == 'Update letter branding'
    assert page.select_one('.error-message').text.strip() == 'Error saving uploaded file - try uploading again'

    assert mock_client_update.call_count == 2
    assert mock_client_update.call_args_list == [
        call(branding_id=fake_uuid, filename='{}-new_file'.format(fake_uuid), name='Updated name'),
        call(branding_id=fake_uuid, filename='hm-government', name='HM Government')
    ]


def test_create_letter_branding_does_not_show_branding_info(logged_in_platform_admin_client):
    response = logged_in_platform_admin_client.get(
        url_for('.create_letter_branding')
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.select_one('#logo-img > img') is None
    assert page.select_one('#name').attrs.get('value') == ''


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
            'operation': 'branding-details'
        }
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.find('h1').text == 'Add letter branding'
    assert page.select_one('.error-message').text.strip() == 'You need to upload a file to submit'


def test_create_letter_branding_persists_logo_when_all_data_is_valid(
    mocker,
    logged_in_platform_admin_client,
    fake_uuid,
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

    response = logged_in_platform_admin_client.post(
        url_for('.create_letter_branding', logo=temp_logo),
        data={
            'name': 'Test brand',
            'operation': 'branding-details'
        },
        follow_redirects=True
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert response.status_code == 200
    assert page.find('h1').text == 'Letter branding'

    mock_letter_client.create_letter_branding.assert_called_once_with(
        filename='{}-test'.format(fake_uuid), name='Test brand'
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


def test_create_letter_branding_shows_form_errors_on_name_field(
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
            'operation': 'branding-details'
        }
    )

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    error_messages = page.find_all('span', class_='error-message')

    assert page.find('h1').text == 'Add letter branding'
    assert len(error_messages) == 1
    assert error_messages[0].text.strip() == 'This field is required.'


def test_create_letter_branding_shows_database_errors_on_name_fields(
    mocker,
    logged_in_platform_admin_client,
    fake_uuid,
):
    with logged_in_platform_admin_client.session_transaction() as session:
        user_id = session["user_id"]

    mocker.patch('app.main.views.letter_branding.get_png_file_from_svg')
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

    response = logged_in_platform_admin_client.post(
        url_for('.create_letter_branding', logo=temp_logo),
        data={
            'name': 'my brand',
            'operation': 'branding-details'
        }
    )

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    error_message = page.find('span', class_='error-message').text.strip()

    assert page.find('h1').text == 'Add letter branding'
    assert error_message == 'name already in use'


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
