from io import BytesIO
from flask import url_for

import moto


def test_choose_sms_template(app_,
                             api_user_active,
                             mock_login,
                             mock_get_user,
                             mock_check_verify_code,
                             mock_get_service_templates):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.choose_sms_template', service_id=12345))

        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert 'template_one' in content
        assert 'template one content' in content
        assert 'template_two' in content
        assert 'template two content' in content


def test_upload_empty_csvfile_returns_to_upload_page(app_,
                                                     api_user_active,
                                                     mock_login,
                                                     mock_get_user,
                                                     mock_get_service_templates,
                                                     mock_check_verify_code,
                                                     mock_get_service_template):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            upload_data = {'file': (BytesIO(''.encode('utf-8')), 'emtpy.csv')}
            response = client.post(url_for('main.send_sms', service_id=12345, template_id=54321),
                                   data=upload_data, follow_redirects=True)

        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert 'The file emtpy.csv contained no data' in content


@moto.mock_s3
def test_upload_csvfile_with_invalid_phone_shows_check_page_with_errors(app_,
                                                                        mocker,
                                                                        api_user_active,
                                                                        mock_login,
                                                                        mock_get_user,
                                                                        mock_get_user_by_email,
                                                                        mock_get_service_template):

    contents = 'phone\n+44 123\n+44 456'
    file_data = (BytesIO(contents.encode('utf-8')), 'invalid.csv')

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            upload_data = {'file': file_data}
            response = client.post(url_for('main.send_sms', service_id=12345, template_id=54321),
                                   data=upload_data,
                                   follow_redirects=True)
        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert 'Your CSV file contained missing or invalid data' in content
        assert '+44 123' in content
        assert '+44 456' in content
        assert 'Choose a CSV file' in content


@moto.mock_s3
def test_send_test_message_to_self(
    app_,
    mocker,
    api_user_active,
    mock_login,
    mock_get_user,
    mock_get_user_by_email,
    mock_get_service_template
):

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(
                url_for('main.send_sms_to_self', service_id=12345, template_id=54321),
                follow_redirects=True
            )
        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert 'Test run' in content
        assert '+4412341234' in content


@moto.mock_s3
def test_download_example_csv(
    app_,
    mocker,
    api_user_active,
    mock_login,
    mock_get_user,
    mock_get_user_by_email,
    mock_get_service_template
):

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(
                url_for('main.get_example_csv', service_id=12345, template_id=54321),
                follow_redirects=True
            )
        assert response.status_code == 200
        assert response.get_data(as_text=True) == 'phone\r\n+4412341234\r\n'
        assert 'text/csv' in response.headers['Content-Type']


@moto.mock_s3
def test_upload_csvfile_with_valid_phone_shows_all_numbers(app_,
                                                           mocker,
                                                           api_user_active,
                                                           mock_login,
                                                           mock_get_user,
                                                           mock_get_user_by_email,
                                                           mock_get_service_template):

    contents = 'phone\n+44 7700 900981\n+44 7700 900982\n+44 7700 900983\n+44 7700 900984\n+44 7700 900985\n+44 7700 900986'  # noqa

    file_data = (BytesIO(contents.encode('utf-8')), 'valid.csv')

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            upload_data = {'file': file_data}
            response = client.post(url_for('main.send_sms', service_id=12345, template_id=54321),
                                   data=upload_data,
                                   follow_redirects=True)

        content = response.get_data(as_text=True)

        assert response.status_code == 200
        assert '+44 7700 900981' in content
        assert '+44 7700 900982' in content
        assert '+44 7700 900983' in content
        assert '+44 7700 900984' in content
        assert '+44 7700 900985' in content
        assert '+44 7700 900986' in content


@moto.mock_s3
def test_create_job_should_call_api(app_,
                                    service_one,
                                    api_user_active,
                                    mock_get_user,
                                    mock_get_user_by_email,
                                    mock_login,
                                    job_data,
                                    mock_create_job,
                                    mock_get_job,
                                    mock_get_service_template):

    service_id = service_one['id']
    job_id = job_data['id']
    original_file_name = job_data['original_file_name']
    template_id = job_data['template']

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            with client.session_transaction() as session:
                session['upload_data'] = {'original_file_name': original_file_name, 'template_id': template_id}
            url = url_for('main.check_sms', service_id=service_one['id'], upload_id=job_id)
            response = client.post(url, data=job_data, follow_redirects=True)

        assert response.status_code == 200
        assert 'We’ve started sending your messages' in response.get_data(as_text=True)
        mock_create_job.assert_called_with(job_id, service_id, template_id, original_file_name)
