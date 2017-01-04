from io import BytesIO
from os import path
from glob import glob
import re
from itertools import repeat
from functools import partial
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from notifications_utils.template import LetterPreviewTemplate

from tests import validate_route_permission

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
    app_,
    api_user_active,
    mocker,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_s3_upload,
    mock_has_permissions,
    fake_uuid
):

    with app_.test_request_context(), app_.test_client() as client, open(filename, 'rb') as uploaded:
        client.login(api_user_active)
        response = client.post(
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
    app_,
    api_user_active,
    mocker,
    mock_login,
    mock_get_service,
    mock_get_service_template_with_placeholders,
    mock_s3_upload,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_detailed_service_for_today,
    fake_uuid
):

    mocker.patch(
        'app.main.views.send.s3download',
        return_value="""
            phone number,name
            +447700900986
            +447700900986
        """
    )

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            initial_upload = client.post(
                url_for('main.send_messages', service_id=fake_uuid, template_id=fake_uuid),
                data={'file': (BytesIO(''.encode('utf-8')), 'invalid.csv')},
                content_type='multipart/form-data',
                follow_redirects=True
            )
            reupload = client.post(
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


def test_upload_csv_invalid_extension(app_,
                                      api_user_active,
                                      mocker,
                                      mock_login,
                                      mock_get_service,
                                      mock_get_service_template,
                                      mock_s3_upload,
                                      mock_has_permissions,
                                      mock_get_users_by_service,
                                      mock_get_detailed_service_for_today,
                                      fake_uuid):

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            resp = client.post(
                url_for('main.send_messages', service_id=fake_uuid, template_id=fake_uuid),
                data={'file': (BytesIO('contents'.encode('utf-8')), 'invalid.txt')},
                content_type='multipart/form-data',
                follow_redirects=True
            )

        assert resp.status_code == 200
        assert "invalid.txt isn’t a spreadsheet that Notify can read" in resp.get_data(as_text=True)


def test_send_test_sms_message(
    app_,
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

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(
                url_for('main.send_test', service_id=fake_uuid, template_id=fake_uuid),
                follow_redirects=True
            )
        assert response.status_code == 200
        mock_s3_upload.assert_called_with(fake_uuid, expected_data, 'eu-west-1')


def test_send_test_email_message(
    app_,
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

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(
                url_for('main.send_test', service_id=fake_uuid, template_id=fake_uuid),
                follow_redirects=True
            )
        assert response.status_code == 200
        mock_s3_upload.assert_called_with(fake_uuid, expected_data, 'eu-west-1')


def test_send_test_sms_message_with_placeholders(
    app_,
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

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.post(
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


def test_api_info_page(
    app_,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_email_template,
    mock_s3_upload,
    mock_has_permissions,
    fake_uuid
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(
                url_for('main.send_from_api', service_id=fake_uuid, template_id=fake_uuid),
                follow_redirects=True
            )
        assert response.status_code == 200
        assert 'API info' in response.get_data(as_text=True)


def test_download_example_csv(
    app_,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_has_permissions,
    fake_uuid
):

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(
                url_for('main.get_example_csv', service_id=fake_uuid, template_id=fake_uuid),
                follow_redirects=True
            )
        assert response.status_code == 200
        assert response.get_data(as_text=True) == 'phone number\r\n07700 900321\r\n'
        assert 'text/csv' in response.headers['Content-Type']


def test_upload_csvfile_with_valid_phone_shows_all_numbers(
    app_,
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

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.post(
                url_for('main.send_messages', service_id=fake_uuid, template_id=fake_uuid),
                data={'file': (BytesIO(''.encode('utf-8')), 'valid.csv')},
                content_type='multipart/form-data',
                follow_redirects=True
            )
            with client.session_transaction() as sess:
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
    app_,
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

    with app_.test_request_context(), app_.test_client() as client:
        client.login(api_user_active)
        with client.session_transaction() as session:
            session['upload_data'] = {
                'original_file_name': 'Test message',
                'template_id': fake_uuid,
                'notification_count': 1,
                'valid': True
            }
        response = client.get(url_for(
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
    app_,
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
    with app_.test_request_context(), app_.test_client() as client:
        client.login(active_user_with_permissions, mocker, service_one)
        with client.session_transaction() as session:
            session['upload_data'] = {
                'original_file_name': original_file_name,
                'template_id': template_id,
                'notification_count': notification_count,
                'valid': True
            }
        url = url_for('main.start_job', service_id=service_one['id'], upload_id=job_id)
        response = client.post(url, data={'scheduled_for': when}, follow_redirects=True)

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


def test_cant_start_letters_job(
    app_,
    client,
    service_one,
    mock_get_service,
    active_user_with_permissions,
    mock_create_job,
    mock_get_service_letter_template,
    mocker,
    fake_uuid
):
    client.login(active_user_with_permissions, mocker, service_one)
    with client.session_transaction() as session:
        session['upload_data'] = {
            'original_file_name': 'example.csv',
            'template_id': fake_uuid,
            'notification_count': 123,
            'valid': True
        }
    response = client.post(
        url_for('main.start_job', service_id=fake_uuid, upload_id=fake_uuid),
        data={}
    )
    assert response.status_code == 403
    mock_create_job.assert_not_called()


@pytest.mark.parametrize(
    'view, expected_content_type',
    [
        ('.check_messages_as_pdf', 'application/pdf'),
        ('.check_messages_as_png', 'image/png'),
    ]
)
@patch('app.utils.LetterPreviewTemplate.jinja_template.render', return_value='')
def test_should_show_preview_letter_message(
    mock_letter_preview,
    view,
    expected_content_type,
    logged_in_client,
    mock_get_service_letter_template,
    mock_get_users_by_service,
    mock_get_detailed_service_for_today,
    fake_uuid,
    mocker,
):

    mocker.patch(
        'app.main.views.send.s3download',
        return_value='\n'.join(
            ['address line 1, postcode'] +
            ['123 street, abc123']
        )
    )

    service_id = fake_uuid
    template_id = fake_uuid
    with logged_in_client.session_transaction() as session:
        session['upload_data'] = {
            'original_file_name': 'example.csv',
            'template_id': fake_uuid,
            'notification_count': 1,
            'valid': True
        }
    response = logged_in_client.get(url_for(view, service_id=service_id, template_type='letter', upload_id=fake_uuid))

    assert response.status_code == 200
    assert response.content_type == expected_content_type
    mock_get_service_letter_template.assert_called_with(service_id, template_id)
    assert mock_letter_preview.call_args[0][0]['message'] == (
        '<h2>Subject</h2>\n'
        '<p>Your vehicle tax is about to expire</p>'
    )


def test_check_messages_should_revalidate_file_when_uploading_file(
    app_,
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
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            with client.session_transaction() as session:
                session['upload_data'] = {'original_file_name': 'invalid.csv',
                                          'template_id': data['template'],
                                          'notification_count': data['notification_count'],
                                          'valid': True}
            response = client.post(
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
def test_route_permissions(mocker,
                           app_,
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
                           response_code):
    with app_.test_request_context():
        validate_route_permission(
            mocker,
            app_,
            "GET",
            response_code,
            url_for(
                route,
                service_id=service_one['id'],
                template_type='sms',
                template_id=fake_uuid),
            ['send_texts', 'send_emails', 'send_letters'],
            api_user_active,
            service_one)


@pytest.mark.parametrize('route', [
    'main.choose_template',
    'main.send_messages',
    'main.get_example_csv',
    'main.send_test'
])
def test_route_invalid_permissions(mocker,
                                   app_,
                                   api_user_active,
                                   service_one,
                                   mock_get_service_template,
                                   mock_get_service_templates,
                                   mock_get_jobs,
                                   mock_get_notifications,
                                   mock_create_job,
                                   fake_uuid,
                                   route):
    with app_.test_request_context():
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


def test_route_choose_template_manage_service_permissions(mocker,
                                                          app_,
                                                          api_user_active,
                                                          service_one,
                                                          mock_login,
                                                          mock_get_user,
                                                          mock_get_service,
                                                          mock_check_verify_code,
                                                          mock_get_service_templates,
                                                          mock_get_jobs):
    with app_.test_request_context():
        template_id = mock_get_service_templates(service_one['id'])['data'][0]['id']
        resp = validate_route_permission(
            mocker,
            app_,
            "GET",
            200,
            url_for(
                'main.choose_template',
                service_id=service_one['id'],
                template_type='sms'),
            ['manage_users', 'manage_templates', 'manage_settings'],
            api_user_active,
            service_one)
        page = resp.get_data(as_text=True)
        assert url_for(
            "main.send_messages",
            service_id=service_one['id'],
            template_id=template_id) not in page
        assert url_for(
            "main.send_test",
            service_id=service_one['id'],
            template_id=template_id) not in page
        assert url_for(
            "main.edit_service_template",
            service_id=service_one['id'],
            template_id=template_id) in page


def test_route_choose_template_send_messages_permissions(mocker,
                                                         app_,
                                                         active_user_with_permissions,
                                                         service_one,
                                                         mock_get_service,
                                                         mock_check_verify_code,
                                                         mock_get_service_templates,
                                                         mock_get_jobs):
    with app_.test_request_context():
        template_id = None
        for temp in mock_get_service_templates(service_one['id'])['data']:
            if temp['template_type'] == 'sms':
                template_id = temp['id']
        assert template_id
        resp = validate_route_permission(
            mocker,
            app_,
            "GET",
            200,
            url_for(
                'main.choose_template',
                service_id=service_one['id'],
                template_type='sms'),
            ['send_texts', 'send_emails', 'send_letters'],
            active_user_with_permissions,
            service_one)
        page = resp.get_data(as_text=True)
        assert url_for(
            "main.send_messages",
            service_id=service_one['id'],
            template_id=template_id) in page
        assert url_for(
            "main.edit_service_template",
            service_id=service_one['id'],
            template_id=template_id) not in page


def test_route_choose_template_manage_api_keys_permissions(mocker,
                                                           app_,
                                                           api_user_active,
                                                           service_one,
                                                           mock_get_user,
                                                           mock_get_service,
                                                           mock_check_verify_code,
                                                           mock_get_service_templates,
                                                           mock_get_jobs):
    with app_.test_request_context():
        template_id = None
        for temp in mock_get_service_templates(service_one['id'])['data']:
            if temp['template_type'] == 'sms':
                template_id = temp['id']
        assert template_id
        resp = validate_route_permission(
            mocker,
            app_,
            "GET",
            200,
            url_for(
                'main.choose_template',
                service_id=service_one['id'],
                template_type='sms'),
            ['manage_api_keys'],
            api_user_active,
            service_one)
        page = resp.get_data(as_text=True)
        assert url_for(
            "main.send_test",
            service_id=service_one['id'],
            template_id=template_id) not in page
        assert url_for(
            "main.edit_service_template",
            service_id=service_one['id'],
            template_id=template_id) not in page
        page = BeautifulSoup(resp.data.decode('utf-8'), 'html.parser')
        links = page.findAll('a', href=re.compile('^' + url_for(
            "main.send_from_api",
            service_id=service_one['id'],
            template_id=template_id)))
        assert len(links) == 1


@pytest.mark.parametrize(
    'extra_args,expected_url',
    [
        (
            dict(),
            partial(url_for, '.send_test')
        ),
        (
            dict(help='0'),
            partial(url_for, '.send_test')
        ),
        (
            dict(help='2'),
            partial(url_for, '.send_test', help='1')
        )
    ]
)
def test_check_messages_back_link(
    app_,
    api_user_active,
    mock_login,
    mock_get_user_by_email,
    mock_get_users_by_service,
    mock_get_service,
    mock_get_service_template_with_placeholders,
    mock_has_permissions,
    mock_get_detailed_service_for_today,
    mock_s3_download,
    fake_uuid,
    extra_args,
    expected_url
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(api_user_active)
        with client.session_transaction() as session:
            session['upload_data'] = {'original_file_name': 'valid.csv',
                                      'template_id': fake_uuid,
                                      'notification_count': 1,
                                      'valid': True}
        response = client.get(url_for(
            'main.check_messages',
            service_id=fake_uuid,
            upload_id=fake_uuid,
            template_type='sms',
            from_test=True,
            **extra_args
        ))
        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert (
            page.findAll('a', {'class': 'page-footer-back-link'})[0]['href']
        ) == expected_url(service_id=fake_uuid, template_id=fake_uuid)


def test_go_to_dashboard_after_tour(
    app_,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_has_permissions,
    mock_delete_service_template,
    fake_uuid
):

    with app_.test_request_context(), app_.test_client() as client:
        client.login(api_user_active)

        resp = client.get(
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
    app_,
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

    with app_.test_request_context(), app_.test_client() as client:
        client.login(api_user_active)
        with client.session_transaction() as session:
            session['upload_data'] = {'original_file_name': 'valid.csv',
                                      'template_id': fake_uuid,
                                      'notification_count': 1,
                                      'valid': True}
        response = client.get(url_for(
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


def test_check_messages_shows_over_max_row_error(
    client,
    app_,
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

    client.login(api_user_active)
    with client.session_transaction() as session:
        session['upload_data'] = {'template_id': fake_uuid}
    response = client.get(url_for(
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
        'Your file has 99,999 rows.'
    )
