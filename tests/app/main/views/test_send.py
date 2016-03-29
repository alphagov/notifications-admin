import pytest

from io import BytesIO
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
    mock_has_permissions
):

    contents = u'phone number,name\n+44 123,test1\n+44 456,test2'
    mocker.patch('app.main.views.send.s3download', return_value=contents)

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.post(
                url_for('main.send_messages', service_id=12345, template_id=54321),
                data={'file': (BytesIO(contents.encode('utf-8')), 'invalid.csv')},
                content_type='multipart/form-data',
                follow_redirects=True
            )
        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert 'There was a problem with invalid.csv' in content
        assert '+44 123' in content
        assert '+44 456' in content
        assert 'Not a UK mobile number' in content
        assert 'Re-upload your file' in content


def test_send_test_message_to_self(
    app_,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_email_template,
    mock_s3_upload,
    mock_has_permissions
):

    expected_data = {'data': 'email address\r\ntest@user.gov.uk\r\n', 'file_name': 'Test run'}
    mocker.patch('app.main.views.send.s3download', return_value='email address\r\ntest@user.gov.uk')

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(
                url_for('main.send_message_to_self', service_id=12345, template_id=54321),
                follow_redirects=True
            )
        assert response.status_code == 200
        mock_s3_upload.assert_called_with(ANY, '12345', expected_data, 'eu-west-1')


def test_send_test_message_from_api_page(
    app_,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_email_template,
    mock_s3_upload,
    mock_has_permissions
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(
                url_for('main.send_from_api', service_id=12345, template_id=54321),
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
    mock_has_permissions
):

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(
                url_for('main.get_example_csv', service_id=12345, template_id=54321),
                follow_redirects=True
            )
        assert response.status_code == 200
        assert response.get_data(as_text=True) == 'phone number\r\n+4412341234\r\n'
        assert 'text/csv' in response.headers['Content-Type']


def test_upload_csvfile_with_valid_phone_shows_all_numbers(
    app_,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_s3_upload,
    mock_has_permissions
):

    mocker.patch(
        'app.main.views.send.s3download',
        return_value="""
            phone number
            +44 7700 9009 01
            +44 7700 9009 02
            +44 7700 9009 03
            +44 7700 9009 04
            +44 7700 9009 05
            +44 7700 9009 06
            +44 7700 9009 07
            +44 7700 9009 08
            +44 7700 9009 09
            +44 7700 9009 10
            +44 7700 9009 11
            +44 7700 9009 12
            +44 7700 9009 13
            +44 7700 9009 14
            +44 7700 9009 15
            +44 7700 9009 99
            +44 7700 9009 99
            +44 7700 9009 99
        """
    )

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.post(
                url_for('main.send_messages', service_id=12345, template_id=54321),
                data={'file': (BytesIO(''.encode('utf-8')), 'valid.csv')},
                content_type='multipart/form-data',
                follow_redirects=True
            )
            with client.session_transaction() as sess:
                assert int(sess['upload_data']['template_id']) == 54321
                assert sess['upload_data']['original_file_name'] == 'valid.csv'
                assert sess['upload_data']['notification_count'] == 18

            content = response.get_data(as_text=True)
            assert response.status_code == 200
            assert '+44 7700 9009 01' in content
            assert '+44 7700 9009 15' in content
            assert '+44 7700 9009 16' not in content
            assert '3 rows not shown' in content


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
    mock_has_permissions
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
                           mock_s3_upload):
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
                    template_id=123),
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
                template_id=123),
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
                                   mock_create_job):
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
                    template_id=123),
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
            ['send_texts', 'send_emails', 'send_letters'],
            active_user_with_permissions,
            service_one)
        page = resp.get_data(as_text=True)
        assert url_for(
            "main.send_messages",
            service_id=service_one['id'],
            template_id=template_id) in page
        assert url_for(
            "main.send_message_to_self",
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
            ['manage_api_keys', 'access_developer_docs'],
            api_user_active,
            service_one)
        page = resp.get_data(as_text=True)
        assert url_for(
            "main.send_messages",
            service_id=service_one['id'],
            template_id=template_id) in page
        assert url_for(
            "main.send_message_to_self",
            service_id=service_one['id'],
            template_id=template_id) not in page
        assert url_for(
            "main.edit_service_template",
            service_id=service_one['id'],
            template_id=template_id) not in page
