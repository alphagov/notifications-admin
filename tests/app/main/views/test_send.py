import uuid
from io import BytesIO
from os import path
from glob import glob
from itertools import repeat
from functools import partial

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from notifications_utils.template import LetterPreviewTemplate

from app.main.views.send import get_check_messages_back_url

from tests import validate_route_permission, template_json
from tests.app.test_utils import normalize_spaces
from tests.conftest import (
    mock_get_service_template,
    mock_get_service_template_with_placeholders,
    mock_get_service_letter_template,
)

template_types = ['email', 'sms']

# The * ignores hidden files, eg .DS_Store
test_spreadsheet_files = glob(path.join('tests', 'spreadsheet_files', '*'))
test_non_spreadsheet_files = glob(path.join('tests', 'non_spreadsheet_files', '*'))


def test_that_test_files_exist():
    assert len(test_spreadsheet_files) == 8
    assert len(test_non_spreadsheet_files) == 6


@pytest.mark.parametrize(
    "filename, acceptable_file",
    list(zip(
        test_spreadsheet_files, repeat(True)
    )) +
    list(zip(
        test_non_spreadsheet_files, repeat(False)
    ))
)
def test_upload_files_in_different_formats(
    filename,
    acceptable_file,
    logged_in_client,
    api_user_active,
    mocker,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_s3_upload,
    mock_has_permissions,
    fake_uuid,
):

    with open(filename, 'rb') as uploaded:
        response = logged_in_client.post(
            url_for('main.send_messages', service_id=fake_uuid, template_id=fake_uuid),
            data={'file': (BytesIO(uploaded.read()), filename)},
            content_type='multipart/form-data'
        )

    if acceptable_file:
        assert mock_s3_upload.call_args[0][1]['data'].strip() == (
            "phone number,name,favourite colour,fruit\r\n"
            "07739 468 050,Pete,Coral,tomato\r\n"
            "07527 125 974,Not Pete,Magenta,Avacado\r\n"
            "07512 058 823,Still Not Pete,Crimson,Pear"
        )
    else:
        assert not mock_s3_upload.called
        assert (
            'Couldn’t read {}. Try using a different file format.'.format(filename)
        ) in response.get_data(as_text=True)


def test_upload_csvfile_with_errors_shows_check_page_with_errors(
    logged_in_client,
    api_user_active,
    mocker,
    mock_login,
    mock_get_service,
    mock_get_service_template_with_placeholders,
    mock_s3_upload,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_detailed_service_for_today,
    fake_uuid,
):

    mocker.patch(
        'app.main.views.send.s3download',
        return_value="""
            phone number,name
            +447700900986
            +447700900986
        """
    )

    initial_upload = logged_in_client.post(
        url_for('main.send_messages', service_id=fake_uuid, template_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'invalid.csv')},
        content_type='multipart/form-data',
        follow_redirects=True
    )
    reupload = logged_in_client.post(
        url_for('main.check_messages', service_id=fake_uuid, template_type='sms', upload_id='abc123'),
        data={'file': (BytesIO(''.encode('utf-8')), 'invalid.csv')},
        content_type='multipart/form-data',
        follow_redirects=True
    )
    for response in [initial_upload, reupload]:
        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert 'There is a problem with your data' in content
        assert '+447700900986' in content
        assert 'Missing' in content
        assert 'Re-upload your file' in content


@pytest.mark.parametrize('file_contents, expected_error,', [
    (
        """
            telephone,name
            +447700900986
        """,
        (
            'Your file needs to have a column called ‘phone number’ '
            'Your file has columns called ‘telephone’ and ‘name’. '
            'Skip to file contents'
        )
    ),
    (
        """
            phone number
            +447700900986
        """,
        (
            'The columns in your file need to match the double brackets in your template '
            'Your file has one column, called ‘phone number’. '
            'It doesn’t have a column called ‘name’. '
            'Skip to file contents'
        )
    ),
    (
        "+447700900986",
        (
            'Your file is missing some rows '
            'It needs at least one row of data, and columns called ‘name’ and ‘phone number’. '
            'Skip to file contents'
        )
    ),
    (
        "",
        (
            'Your file is missing some rows '
            'It needs at least one row of data, and columns called ‘name’ and ‘phone number’. '
            'Skip to file contents'
        )
    ),
])
def test_upload_csvfile_with_missing_columns_shows_error(
    logged_in_client,
    mocker,
    mock_get_service_template_with_placeholders,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_detailed_service_for_today,
    service_one,
    fake_uuid,
    file_contents,
    expected_error,
):

    mocker.patch('app.main.views.send.s3download', return_value=file_contents)

    response = logged_in_client.post(
        url_for('main.send_messages', service_id=service_one['id'], template_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'invalid.csv')},
        follow_redirects=True,
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert ' '.join(page.select('.banner-dangerous')[0].text.split()) == expected_error


def test_upload_csv_invalid_extension(
    logged_in_client,
    api_user_active,
    mocker,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_s3_upload,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_detailed_service_for_today,
    fake_uuid,
):

    resp = logged_in_client.post(
        url_for('main.send_messages', service_id=fake_uuid, template_id=fake_uuid),
        data={'file': (BytesIO('contents'.encode('utf-8')), 'invalid.txt')},
        content_type='multipart/form-data',
        follow_redirects=True
    )

    assert resp.status_code == 200
    assert "invalid.txt isn’t a spreadsheet that Notify can read" in resp.get_data(as_text=True)


def test_upload_valid_csv_shows_page_title(
    logged_in_client,
    mocker,
    mock_get_service_template_with_placeholders,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_detailed_service_for_today,
    service_one,
    fake_uuid,
):

    mocker.patch('app.main.views.send.s3download', return_value="""
        phone number,name\n07700900986,Jo
    """)

    response = logged_in_client.post(
        url_for('main.send_messages', service_id=service_one['id'], template_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'valid.csv')},
        follow_redirects=True,
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.text.strip() == 'Preview of Two week reminder'


def test_upload_valid_csv_shows_file_contents(
    logged_in_client,
    mocker,
    mock_get_service_template_with_placeholders,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_detailed_service_for_today,
    service_one,
    fake_uuid,
):

    mocker.patch('app.main.views.send.s3download', return_value="""
        phone number,name,thing,thing,thing
        07700900986, Jo,  foo,  foo,  foo
    """)

    response = logged_in_client.post(
        url_for('main.send_messages', service_id=service_one['id'], template_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'valid.csv')},
        follow_redirects=True,
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    for index, cell in enumerate([
        '<td class="table-field-index"> <span>2</span> </td>',
        '<td class="table-field-center-aligned "> <div class=""> 07700900986 </div> </td>',
        '<td class="table-field-center-aligned "> <div class=""> Jo </div> </td>',
        (
            '<td class="table-field-center-aligned "> '
            '<div class="table-field-status-default"> '
            '<ul class="list list-bullet"> '
            '<li>foo</li> <li>foo</li> <li>foo</li> '
            '</ul> '
            '</div> '
            '</td>'
        ),
    ]):
        assert normalize_spaces(str(page.select('table tbody td')[index])) == cell


def test_send_test_sms_message(
    logged_in_client,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_s3_upload,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_detailed_service_for_today,
    fake_uuid
):

    expected_data = {'data': 'phone number\r\n07700 900 762\r\n', 'file_name': 'Test message'}
    mocker.patch('app.main.views.send.s3download', return_value='phone number\r\n+4412341234')

    response = logged_in_client.get(
        url_for('main.send_test', service_id=fake_uuid, template_id=fake_uuid),
        follow_redirects=True
    )
    assert response.status_code == 200
    mock_s3_upload.assert_called_with(fake_uuid, expected_data, 'eu-west-1')


def test_send_test_email_message(
    logged_in_client,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_email_template_without_placeholders,
    mock_s3_upload,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_detailed_service_for_today,
    fake_uuid
):

    expected_data = {'data': 'email address\r\ntest@user.gov.uk\r\n', 'file_name': 'Test message'}
    mocker.patch('app.main.views.send.s3download', return_value='email address\r\ntest@user.gov.uk')

    response = logged_in_client.get(
        url_for('main.send_test', service_id=fake_uuid, template_id=fake_uuid),
        follow_redirects=True
    )
    assert response.status_code == 200
    mock_s3_upload.assert_called_with(fake_uuid, expected_data, 'eu-west-1')


def test_send_test_sms_message_with_placeholders(
    logged_in_client,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_template_with_placeholders,
    mock_s3_upload,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_detailed_service_for_today,
    fake_uuid
):

    expected_data = {
        'data': 'phone number,name\r\n07700 900 762,Jo\r\n',
        'file_name': 'Test message'
    }
    mocker.patch('app.main.views.send.s3download', return_value='phone number\r\n+4412341234')

    response = logged_in_client.post(
        url_for(
            'main.send_test',
            service_id=fake_uuid,
            template_id=fake_uuid
        ),
        data={'name': 'Jo'},
        follow_redirects=True
    )
    assert response.status_code == 200
    mock_s3_upload.assert_called_with(fake_uuid, expected_data, 'eu-west-1')


def test_download_example_csv(
    logged_in_client,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_has_permissions,
    fake_uuid
):

    response = logged_in_client.get(
        url_for('main.get_example_csv', service_id=fake_uuid, template_id=fake_uuid),
        follow_redirects=True
    )
    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'phone number\r\n07700 900321\r\n'
    assert 'text/csv' in response.headers['Content-Type']


def test_upload_csvfile_with_valid_phone_shows_all_numbers(
    logged_in_client,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_s3_upload,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_detailed_service_for_today,
    fake_uuid
):

    mocker.patch(
        'app.main.views.send.s3download',
        return_value='\n'.join(['phone number'] + [
            '07700 9007{0:02d}'.format(final_two) for final_two in range(0, 53)
        ])
    )

    response = logged_in_client.post(
        url_for('main.send_messages', service_id=fake_uuid, template_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'valid.csv')},
        content_type='multipart/form-data',
        follow_redirects=True
    )
    with logged_in_client.session_transaction() as sess:
        assert sess['upload_data']['template_id'] == fake_uuid
        assert sess['upload_data']['original_file_name'] == 'valid.csv'
        assert sess['upload_data']['notification_count'] == 53

    content = response.get_data(as_text=True)
    assert response.status_code == 200
    assert '07700 900701' in content
    assert '07700 900749' in content
    assert '07700 900750' not in content
    assert 'Only showing the first 50 rows' in content

    mock_get_detailed_service_for_today.assert_called_once_with(fake_uuid)


def test_test_message_can_only_be_sent_now(
    logged_in_client,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_s3_download,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_detailed_service_for_today,
    fake_uuid
):

    with logged_in_client.session_transaction() as session:
        session['upload_data'] = {
            'original_file_name': 'Test message',
            'template_id': fake_uuid,
            'notification_count': 1,
            'valid': True
        }
    response = logged_in_client.get(url_for(
        'main.check_messages',
        service_id=fake_uuid,
        upload_id=fake_uuid,
        template_type='sms',
        from_test=True
    ))

    content = response.get_data(as_text=True)
    assert 'name="scheduled_for"' not in content


@pytest.mark.parametrize(
    'when', [
        '', '2016-08-25T13:04:21.767198'
    ]
)
def test_create_job_should_call_api(
    logged_in_client,
    service_one,
    active_user_with_permissions,
    mock_create_job,
    mock_get_job,
    mock_get_notifications,
    mock_get_service_template,
    mocker,
    fake_uuid,
    when
):
    service_id = service_one['id']
    data = mock_get_job(service_one['id'], fake_uuid)['data']
    job_id = data['id']
    original_file_name = data['original_file_name']
    template_id = data['template']
    notification_count = data['notification_count']
    with logged_in_client.session_transaction() as session:
        session['upload_data'] = {
            'original_file_name': original_file_name,
            'template_id': template_id,
            'notification_count': notification_count,
            'valid': True
        }
    url = url_for('main.start_job', service_id=service_one['id'], upload_id=job_id)
    response = logged_in_client.post(url, data={'scheduled_for': when}, follow_redirects=True)

    assert response.status_code == 200
    assert original_file_name in response.get_data(as_text=True)
    mock_create_job.assert_called_with(
        job_id,
        service_id,
        template_id,
        original_file_name,
        notification_count,
        scheduled_for=when
    )


def test_can_start_letters_job(
    logged_in_platform_admin_client,
    mock_create_job,
    service_one,
    fake_uuid
):

    with logged_in_platform_admin_client.session_transaction() as session:
        session['upload_data'] = {
            'original_file_name': 'example.csv',
            'template_id': fake_uuid,
            'notification_count': 123,
            'valid': True
        }
    response = logged_in_platform_admin_client.post(
        url_for('main.start_job', service_id=service_one['id'], upload_id=fake_uuid),
        data={}
    )
    assert response.status_code == 302


@pytest.mark.parametrize('filetype', ['pdf', 'png'])
def test_should_show_preview_letter_message(
    filetype,
    logged_in_platform_admin_client,
    mock_get_service_letter_template,
    mock_get_users_by_service,
    mock_get_detailed_service_for_today,
    service_one,
    fake_uuid,
    mocker,
):
    service_one['can_send_letters'] = True
    mocker.patch('app.service_api_client.get_service', return_value={"data": service_one})

    mocker.patch(
        'app.main.views.send.s3download',
        return_value='\n'.join(
            ['address line 1, postcode'] +
            ['123 street, abc123']
        )
    )
    mocked_preview = mocker.patch(
        'app.main.views.send.TemplatePreview.from_utils_template',
        return_value='foo'
    )

    service_id = service_one['id']
    template_id = fake_uuid
    with logged_in_platform_admin_client.session_transaction() as session:
        session['upload_data'] = {
            'original_file_name': 'example.csv',
            'template_id': fake_uuid,
            'notification_count': 1,
            'valid': True
        }
    response = logged_in_platform_admin_client.get(
        url_for(
            'main.check_messages_preview',
            service_id=service_id,
            template_type='letter',
            upload_id=fake_uuid,
            filetype=filetype
        )
    )

    mock_get_service_letter_template.assert_called_with(service_id, template_id)

    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'foo'
    assert mocked_preview.call_args[0][0].id == template_id
    assert type(mocked_preview.call_args[0][0]) == LetterPreviewTemplate
    assert mocked_preview.call_args[0][1] == filetype


def test_check_messages_should_revalidate_file_when_uploading_file(
    logged_in_client,
    service_one,
    active_user_with_permissions,
    mock_create_job,
    mock_get_job,
    mock_get_service_template_with_placeholders,
    mock_s3_upload,
    mocker,
    mock_has_permissions,
    mock_get_detailed_service_for_today,
    mock_get_users_by_service,
    fake_uuid
):

    service_id = service_one['id']

    mocker.patch(
        'app.main.views.send.s3download',
        return_value="""
            phone number,name,,,
            +447700900986,,,,
            +447700900986,,,,
        """
    )
    data = mock_get_job(service_one['id'], fake_uuid)['data']
    with logged_in_client.session_transaction() as session:
        session['upload_data'] = {'original_file_name': 'invalid.csv',
                                  'template_id': data['template'],
                                  'notification_count': data['notification_count'],
                                  'valid': True}
    response = logged_in_client.post(
        url_for('main.start_job', service_id=service_id, upload_id=data['id']),
        data={'file': (BytesIO(''.encode('utf-8')), 'invalid.csv')},
        content_type='multipart/form-data',
        follow_redirects=True
    )
    assert response.status_code == 200
    assert 'There is a problem with your data' in response.get_data(as_text=True)


@pytest.mark.parametrize('route, response_code', [
    ('main.choose_template', 200),
    ('main.send_messages', 200),
    ('main.get_example_csv', 200),
    ('main.send_test', 302)
])
def test_route_permissions(
    mocker,
    app_,
    client,
    api_user_active,
    service_one,
    mock_get_service_template,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_notifications,
    mock_create_job,
    mock_s3_upload,
    fake_uuid,
    route,
    response_code,
):
    validate_route_permission(
        mocker,
        app_,
        "GET",
        response_code,
        url_for(
            route,
            service_id=service_one['id'],
            template_id=fake_uuid
        ),
        ['send_texts', 'send_emails', 'send_letters'],
        api_user_active,
        service_one)


@pytest.mark.parametrize('route', [
    'main.choose_template',
    'main.send_messages',
    'main.get_example_csv',
    'main.send_test'
])
def test_route_invalid_permissions(
    mocker,
    app_,
    client,
    api_user_active,
    service_one,
    mock_get_service_template,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_notifications,
    mock_create_job,
    fake_uuid,
    route,
):
    validate_route_permission(
        mocker,
        app_,
        "GET",
        403,
        url_for(
            route,
            service_id=service_one['id'],
            template_type='sms',
            template_id=fake_uuid),
        ['blah'],
        api_user_active,
        service_one)


@pytest.mark.parametrize(
    'template_mock, extra_args, expected_url',
    [
        (
            mock_get_service_template,
            dict(),
            partial(url_for, '.send_messages')
        ),
        (
            mock_get_service_template_with_placeholders,
            dict(),
            partial(url_for, '.send_messages')
        ),
        (
            mock_get_service_template,
            dict(from_test=True),
            partial(url_for, '.view_template')
        ),
        (
            mock_get_service_letter_template,  # No placeholders
            dict(from_test=True),
            partial(url_for, '.send_test')
        ),
        (
            mock_get_service_template_with_placeholders,
            dict(from_test=True),
            partial(url_for, '.send_test')
        ),
        (
            mock_get_service_template_with_placeholders,
            dict(help='0', from_test=True),
            partial(url_for, '.send_test')
        ),
        (
            mock_get_service_template_with_placeholders,
            dict(help='2', from_test=True),
            partial(url_for, '.send_test', help='1')
        )
    ]
)
def test_check_messages_back_link(
    logged_in_client,
    api_user_active,
    mock_login,
    mock_get_user_by_email,
    mock_get_users_by_service,
    mock_get_service,
    mock_has_permissions,
    mock_get_detailed_service_for_today,
    mock_s3_download,
    fake_uuid,
    mocker,
    template_mock,
    extra_args,
    expected_url
):
    template_mock(mocker)
    with logged_in_client.session_transaction() as session:
        session['upload_data'] = {'original_file_name': 'valid.csv',
                                  'template_id': fake_uuid,
                                  'notification_count': 1,
                                  'valid': True}
    response = logged_in_client.get(url_for(
        'main.check_messages',
        service_id=fake_uuid,
        upload_id=fake_uuid,
        template_type='sms',
        **extra_args
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert (
        page.findAll('a', {'class': 'page-footer-back-link'})[0]['href']
    ) == expected_url(service_id=fake_uuid, template_id=fake_uuid)


def test_go_to_dashboard_after_tour(
    logged_in_client,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_has_permissions,
    mock_delete_service_template,
    fake_uuid
):

    resp = logged_in_client.get(
        url_for('main.go_to_dashboard_after_tour', service_id=fake_uuid, example_template_id=fake_uuid)
    )

    assert resp.status_code == 302
    assert resp.location == url_for("main.service_dashboard", service_id=fake_uuid, _external=True)
    mock_delete_service_template.assert_called_once_with(fake_uuid, fake_uuid)


@pytest.mark.parametrize('num_requested,expected_msg', [
    (0, '‘valid.csv’ contains 100 phone numbers.'),
    (1, 'You can still send 49 messages today, but ‘valid.csv’ contains 100 phone numbers.')
], ids=['none_sent', 'some_sent'])
def test_check_messages_shows_too_many_messages_errors(
    mocker,
    logged_in_client,
    api_user_active,
    mock_login,
    mock_get_users_by_service,
    mock_get_service,
    mock_get_service_template,
    mock_has_permissions,
    fake_uuid,
    num_requested,
    expected_msg
):
    # csv with 100 phone numbers
    mocker.patch('app.main.views.send.s3download', return_value=',\n'.join(
        ['phone number'] + ([mock_get_users_by_service(None)[0]._mobile_number]*100)
    ))
    mocker.patch('app.service_api_client.get_detailed_service_for_today', return_value={
        'data': {
            'statistics': {
                'sms': {'requested': num_requested, 'delivered': 0, 'failed': 0},
                'email': {'requested': 0, 'delivered': 0, 'failed': 0}
            }
        }
    })

    with logged_in_client.session_transaction() as session:
        session['upload_data'] = {'original_file_name': 'valid.csv',
                                  'template_id': fake_uuid,
                                  'notification_count': 1,
                                  'valid': True}
    response = logged_in_client.get(url_for(
        'main.check_messages',
        service_id=fake_uuid,
        template_type='sms',
        upload_id=fake_uuid
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('h1').text.strip() == 'Too many recipients'
    assert page.find('div', class_='banner-dangerous').find('a').text.strip() == 'trial mode'

    # remove excess whitespace from element
    details = page.find('div', class_='banner-dangerous').findAll('p')[1]
    details = ' '.join([line.strip() for line in details.text.split('\n') if line.strip() != ''])
    assert details == expected_msg


def test_check_messages_shows_trial_mode_error(
    logged_in_client,
    mock_get_users_by_service,
    mock_get_service,
    mock_get_service_template,
    mock_has_permissions,
    mock_get_detailed_service_for_today,
    mocker
):
    mocker.patch('app.main.views.send.s3download', return_value=(
        'phone number,\n07900900321'  # Not in team
    ))
    with logged_in_client.session_transaction() as session:
        session['upload_data'] = {'template_id': ''}
    response = logged_in_client.get(url_for(
        'main.check_messages',
        service_id=uuid.uuid4(),
        template_type='sms',
        upload_id=uuid.uuid4()
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert ' '.join(
        page.find('div', class_='banner-dangerous').text.split()
    ) == (
        'You can’t send to this phone number '
        'In trial mode you can only send to yourself and members of your team '
        'Skip to file contents'
    )


def test_check_messages_shows_over_max_row_error(
    logged_in_client,
    api_user_active,
    mock_login,
    mock_get_users_by_service,
    mock_get_service,
    mock_get_service_template_with_placeholders,
    mock_has_permissions,
    mock_get_detailed_service_for_today,
    mock_s3_download,
    fake_uuid,
    mocker
):
    mock_recipients = mocker.patch('app.main.views.send.RecipientCSV').return_value
    mock_recipients.max_rows = 11111
    mock_recipients.__len__.return_value = 99999
    mock_recipients.too_many_rows.return_value = True

    with logged_in_client.session_transaction() as session:
        session['upload_data'] = {'template_id': fake_uuid}
    response = logged_in_client.get(url_for(
        'main.check_messages',
        service_id=fake_uuid,
        template_type='sms',
        upload_id=fake_uuid
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert ' '.join(
        page.find('div', class_='banner-dangerous').text.split()
    ) == (
        'Your file has too many rows '
        'Notify can process up to 11,111 rows at once. '
        'Your file has 99,999 rows. '
        'Skip to file contents'
    )


def test_check_messages_redirects_if_no_upload_data(logged_in_client, service_one, mocker):
    checker = mocker.patch('app.main.views.send.get_check_messages_back_url', return_value='foo')
    response = logged_in_client.get(url_for(
        'main.check_messages',
        service_id=service_one['id'],
        template_type='bar',
        upload_id='baz'
    ))

    checker.assert_called_once_with(service_one['id'], 'bar')
    assert response.status_code == 301
    assert response.location == 'http://localhost/foo'


@pytest.mark.parametrize('template_type', ['sms', 'email'])
def test_get_check_messages_back_url_returns_to_correct_select_template(client, mocker, template_type):
    mocker.patch('app.main.views.send.get_help_argument', return_value=False)

    assert get_check_messages_back_url('1234', template_type) == url_for(
        'main.choose_template',
        service_id='1234'
    )


def test_check_messages_back_from_help_goes_to_start_of_help(client, service_one, mocker):
    mocker.patch('app.main.views.send.get_help_argument', return_value=True)
    mocker.patch('app.service_api_client.get_service_templates', lambda service_id: {
        'data': [template_json(service_one['id'], '111', type_='sms')]
    })
    assert get_check_messages_back_url(service_one['id'], 'sms') == url_for(
        'main.send_test',
        service_id=service_one['id'],
        template_id='111',
        help='1'
    )


@pytest.mark.parametrize('templates', [
    [],
    [
        template_json('000', '111', type_='sms'),
        template_json('000', '222', type_='sms')
    ]
], ids=['no_templates', 'two_templates'])
def test_check_messages_back_from_help_handles_unexpected_templates(client, mocker, templates):
    mocker.patch('app.main.views.send.get_help_argument', return_value=True)
    mocker.patch('app.service_api_client.get_service_templates', lambda service_id: {
        'data': templates
    })

    assert get_check_messages_back_url('1234', 'sms') == url_for(
        'main.choose_template',
        service_id='1234',
    )
