from io import BytesIO
from flask import url_for

import moto


def test_upload_empty_csvfile_returns_to_upload_page(app_,
                                                     db_,
                                                     db_session,
                                                     mock_send_sms,
                                                     mock_active_user,
                                                     mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(mock_active_user)
            upload_data = {'file': (BytesIO(''.encode('utf-8')), 'emtpy.csv')}
            response = client.post(url_for('main.send_sms', service_id=123),
                                   data=upload_data, follow_redirects=True)

        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert 'The file emtpy.csv contained no data' in content


@moto.mock_s3
def test_upload_csvfile_with_invalid_phone_shows_check_page_with_errors(app_,
                                                                        mock_active_user,
                                                                        mock_get_by_email):

    contents = 'phone\n+44 123\n+44 456'
    file_data = (BytesIO(contents.encode('utf-8')), 'invalid.csv')

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(mock_active_user)
            upload_data = {'file': file_data}
            response = client.post(url_for('main.send_sms', service_id=123),
                                   data=upload_data,
                                   follow_redirects=True)
        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert 'The following numbers are invalid' in content
        assert '+44 123' in content
        assert '+44 456' in content
        assert 'Go back and resolve errors' in content


@moto.mock_s3
def test_upload_csvfile_with_valid_phone_shows_first3_and_last3_numbers(app_,
                                                                        mocker,
                                                                        mock_active_user,
                                                                        mock_get_by_email):

    contents = 'phone\n+44 7700 900981\n+44 7700 900982\n+44 7700 900983\n+44 7700 900984\n+44 7700 900985\n+44 7700 900986\n+44 7700 900987\n+44 7700 900988\n+44 7700 900989'  # noqa

    file_data = (BytesIO(contents.encode('utf-8')), 'valid.csv')

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(mock_active_user)
            upload_data = {'file': file_data}
            response = client.post(url_for('main.send_sms', service_id=123),
                                   data=upload_data,
                                   follow_redirects=True)

        content = response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'Check and confirm' in content
        assert 'First three message in file' in content
        assert 'Last three messages in file' in content
        assert '+44 7700 900981' in content
        assert '+44 7700 900982' in content
        assert '+44 7700 900983' in content
        assert '+44 7700 900984' not in content
        assert '+44 7700 900985' not in content
        assert '+44 7700 900986' not in content
        assert '+44 7700 900987' in content
        assert '+44 7700 900988' in content
        assert '+44 7700 900989' in content


@moto.mock_s3
def test_upload_csvfile_with_valid_phone_shows_all_if_6_or_less_numbers(app_,
                                                                        mocker,
                                                                        mock_active_user,
                                                                        mock_get_by_email):

    contents = 'phone\n+44 7700 900981\n+44 7700 900982\n+44 7700 900983\n+44 7700 900984\n+44 7700 900985\n+44 7700 900986'  # noqa

    file_data = (BytesIO(contents.encode('utf-8')), 'valid.csv')

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(mock_active_user)
            upload_data = {'file': file_data}
            response = client.post(url_for('main.send_sms', service_id=123),
                                   data=upload_data,
                                   follow_redirects=True)

        content = response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'Check and confirm' in content
        assert 'All messages in file' in content
        assert '+44 7700 900981' in content
        assert '+44 7700 900982' in content
        assert '+44 7700 900983' in content
        assert '+44 7700 900984' in content
        assert '+44 7700 900985' in content
        assert '+44 7700 900986' in content


@moto.mock_s3
def test_should_redirect_to_job(app_,
                                mock_active_user,
                                mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(mock_active_user)
            response = client.post(url_for('main.check_sms',
                                           service_id=123,
                                           upload_id='someid'))
        assert response.status_code == 302
