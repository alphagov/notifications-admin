import pytest
import re
from io import BytesIO
from bs4 import BeautifulSoup
from flask import url_for
from unittest.mock import ANY
from tests import validate_route_permission

template_types = ['email', 'sms']


def test_upload_csvfile_with_errors_shows_check_page_with_errors(
    app_,
    api_user_active,
    mocker,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_s3_upload,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_service_statistics,
    fake_uuid
):

    contents = u'phone number,name\n+44 123,test1\n+44 456,test2'
    mocker.patch('app.main.views.send.s3download', return_value=contents)

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            initial_upload = client.post(
                url_for('main.send_messages', service_id=fake_uuid, template_id=fake_uuid),
                data={'file': (BytesIO(contents.encode('utf-8')), 'invalid.csv')},
                content_type='multipart/form-data',
                follow_redirects=True
            )
            reupload = client.post(
                url_for('main.check_messages', service_id=fake_uuid, template_type='sms', upload_id='abc123'),
                data={'file': (BytesIO(contents.encode('utf-8')), 'invalid.csv')},
                content_type='multipart/form-data',
                follow_redirects=True
            )
        for response in [initial_upload, reupload]:
            assert response.status_code == 200
            content = response.get_data(as_text=True)
            assert 'There was a problem with invalid.csv' in content
            assert '+44 123' in content
            assert '+44 456' in content
            assert 'Not a UK mobile number' in content
            assert 'Re-upload your file' in content


def test_upload_csv_invalid_extension(app_,
                                      api_user_active,
                                      mock_login,
                                      mock_get_service,
                                      mock_get_service_template,
                                      mock_s3_upload,
                                      mock_has_permissions,
                                      mock_get_users_by_service,
                                      mock_get_service_statistics,
                                      fake_uuid):
    contents = u'phone number,name\n+44 123,test1\n+44 456,test2'
    with app_.test_request_context():
        filename = 'invalid.txt'
        with app_.test_client() as client:
            client.login(api_user_active)
            resp = client.post(
                url_for('main.send_messages', service_id=fake_uuid, template_id=fake_uuid),
                data={'file': (BytesIO(contents.encode('utf-8')), filename)},
                content_type='multipart/form-data',
                follow_redirects=True
            )

        assert resp.status_code == 200
        assert "{} is not a CSV file".format(filename) in resp.get_data(as_text=True)


def test_send_test_sms_message_to_self(
    app_,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_s3_upload,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_service_statistics,
    fake_uuid
):

    expected_data = {'data': 'phone number\r\n07700 900 762\r\n', 'file_name': 'Test run'}
    mocker.patch('app.main.views.send.s3download', return_value='phone number\r\n+4412341234')

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(
                url_for('main.send_message_to_self', service_id=fake_uuid, template_id=fake_uuid),
                follow_redirects=True
            )
        assert response.status_code == 200
        mock_s3_upload.assert_called_with(ANY, fake_uuid, expected_data, 'eu-west-1')


def test_send_test_email_message_to_self(
    app_,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_email_template,
    mock_s3_upload,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_service_statistics,
    fake_uuid
):

    expected_data = {'data': 'email address\r\ntest@user.gov.uk\r\n', 'file_name': 'Test run'}
    mocker.patch('app.main.views.send.s3download', return_value='email address\r\ntest@user.gov.uk')

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(
                url_for('main.send_message_to_self', service_id=fake_uuid, template_id=fake_uuid),
                follow_redirects=True
            )
        assert response.status_code == 200
        mock_s3_upload.assert_called_with(ANY, fake_uuid, expected_data, 'eu-west-1')


def test_send_test_message_from_api_page(
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
        assert 'API integration' in response.get_data(as_text=True)


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
        assert response.get_data(as_text=True) == 'phone number\r\n07700 900 762\r\n07700 900 762\r\n'
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
    mock_get_service_statistics,
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
            assert 'Only showing the first 50 rows with errors' in content


def test_create_job_should_call_api(
    app_,
    service_one,
    api_user_active,
    mock_login,
    job_data,
    mock_create_job,
    mock_get_job,
    mock_get_notifications,
    mock_get_service,
    mock_get_service_template,
    mock_has_permissions
):

    service_id = service_one['id']
    job_id = job_data['id']
    original_file_name = job_data['original_file_name']
    template_id = job_data['template']
    notification_count = job_data['notification_count']

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            with client.session_transaction() as session:
                session['upload_data'] = {'original_file_name': original_file_name,
                                          'template_id': template_id,
                                          'notification_count': notification_count,
                                          'valid': True}
            url = url_for('main.start_job', service_id=service_one['id'], upload_id=job_id)
            response = client.post(url, data=job_data, follow_redirects=True)

        assert response.status_code == 200
        assert original_file_name in response.get_data(as_text=True)
        mock_create_job.assert_called_with(job_id, service_id, template_id, original_file_name, notification_count)


def test_check_messages_should_revalidate_file_when_uploading_file(
    app_,
    service_one,
    api_user_active,
    mock_login,
    mock_get_service,
    job_data,
    mock_create_job,
    mock_get_service_template,
    mock_s3_upload,
    mocker,
    mock_has_permissions,
    mock_get_service_statistics,
    mock_get_users_by_service
):

    service_id = service_one['id']

    mocker.patch(
        'app.main.views.send.s3download',
        return_value="""
            phone number,name,,,
            123,test1,,,
            123,test2,,,
        """
    )
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            with client.session_transaction() as session:
                session['upload_data'] = {'original_file_name': 'invalid.csv',
                                          'template_id': job_data['template'],
                                          'notification_count': job_data['notification_count'],
                                          'valid': True}
            response = client.post(
                url_for('main.start_job', service_id=service_id, upload_id=job_data['id']),
                data={'file': (BytesIO(''.encode('utf-8')), 'invalid.csv')},
                content_type='multipart/form-data',
                follow_redirects=True
            )
            assert response.status_code == 200
            assert 'There was a problem with invalid.csv' in response.get_data(as_text=True)


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
                           fake_uuid):
    routes = [
        'main.choose_template',
        'main.send_messages',
        'main.get_example_csv']
    with app_.test_request_context():
        for route in routes:
            validate_route_permission(
                mocker,
                app_,
                "GET",
                200,
                url_for(
                    route,
                    service_id=service_one['id'],
                    template_type='sms',
                    template_id=fake_uuid),
                ['send_texts', 'send_emails', 'send_letters'],
                api_user_active,
                service_one)

    with app_.test_request_context():
        validate_route_permission(
            mocker,
            app_,
            "GET",
            302,
            url_for(
                'main.send_message_to_self',
                service_id=service_one['id'],
                template_type='sms',
                template_id=fake_uuid),
            ['send_texts', 'send_emails', 'send_letters'],
            api_user_active,
            service_one)


def test_route_invalid_permissions(mocker,
                                   app_,
                                   api_user_active,
                                   service_one,
                                   mock_get_service_template,
                                   mock_get_service_templates,
                                   mock_get_jobs,
                                   mock_get_notifications,
                                   mock_create_job,
                                   fake_uuid):
    routes = [
        'main.choose_template',
        'main.send_messages',
        'main.get_example_csv',
        'main.send_message_to_self']
    with app_.test_request_context():
        for route in routes:
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
            "main.send_message_to_self",
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
            "main.send_message_to_self",
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
