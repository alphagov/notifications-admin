from io import BytesIO
from unittest import mock
from unittest.mock import mock_open

from tests.app.main import create_test_user


def test_upload_empty_csvfile_returns_to_upload_page(
        notifications_admin, notifications_admin_db, notify_db_session,
        mocker):

    _setup_mocker_for_empty_file(mocker)
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            upload_data = {'file': (BytesIO(''.encode('utf-8')), 'emtpy.csv')}
            response = client.post('/services/123/sms/send',
                                   data=upload_data, follow_redirects=True)

        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert 'The file emtpy.csv contained no data' in content


def test_upload_csvfile_with_invalid_phone_shows_check_page_with_errors(
        notifications_admin, notifications_admin_db, notify_db_session,
        mocker):

    contents = 'phone\n+44 123\n+44 456'
    file_data = (BytesIO(contents.encode('utf-8')), 'invalid.csv')
    m_open = mock_open(read_data=contents)
    _setup_mocker_for_nonemtpy_file(mocker)

    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            upload_data = {'file': file_data}
            with mock.patch('app.main.views.sms._open', m_open):
                response = client.post('/services/123/sms/send',
                                       data=upload_data,
                                       follow_redirects=True)
        assert response.status_code == 200
        content = response.get_data(as_text=True)

        assert 'There was a problem with some of the numbers' in content
        assert 'The following numbers are invalid' in content
        assert '+44 123' in content
        assert '+44 456' in content
        assert 'Go back and resolve errors' in content


def test_upload_csvfile_with_valid_phone_shows_first3_and_last3_numbers(
        notifications_admin, notifications_admin_db, notify_db_session,
        mocker):

    contents = 'phone\n+44 7700 900981\n+44 7700 900982\n+44 7700 900983\n+44 7700 900984\n+44 7700 900985\n+44 7700 900986\n+44 7700 900987\n+44 7700 900988\n+44 7700 900989'  # noqa

    file_data = (BytesIO(contents.encode('utf-8')), 'valid.csv')
    m_open = mock_open(read_data=contents)
    _setup_mocker_for_nonemtpy_file(mocker)

    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            upload_data = {'file': file_data}
            with mock.patch('app.main.views.sms._open', m_open):
                response = client.post('/services/123/sms/send',
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


def test_upload_csvfile_with_valid_phone_shows_all_if_6_or_less_numbers(
        notifications_admin, notifications_admin_db, notify_db_session,
        mocker):

    contents = 'phone\n+44 7700 900981\n+44 7700 900982\n+44 7700 900983\n+44 7700 900984\n+44 7700 900985\n+44 7700 900986'  # noqa

    file_data = (BytesIO(contents.encode('utf-8')), 'valid.csv')
    m_open = mock_open(read_data=contents)
    _setup_mocker_for_nonemtpy_file(mocker)

    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            upload_data = {'file': file_data}
            with mock.patch('app.main.views.sms._open', m_open):
                response = client.post('/services/123/sms/send',
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


def test_should_redirect_to_job(notifications_admin, notifications_admin_db,
                                notify_db_session, mocker):
    _setup_mocker_for_check(mocker)
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            with client.session_transaction() as s:
                s[456] = 'test.csv'

        response = client.post('/services/123/sms/check',
                               data={'recipients': 'test.csv'})

        assert response.status_code == 302


def _setup_mocker_for_empty_file(mocker):
    mocker.patch('werkzeug.datastructures.FileStorage.save')
    mocker.patch('os.remove')
    ret = ValueError('The file emtpy.csv contained no data')
    mocker.patch('app.main.views.sms._check_file', side_effect=ret)


def _setup_mocker_for_nonemtpy_file(mocker):
    mocker.patch('werkzeug.datastructures.FileStorage.save')
    mocker.patch('os.remove')
    mocker.patch('app.main.views.sms._check_file')


def _setup_mocker_for_check(mocker):
    mocker.patch('app.main.views.sms.s3upload').return_value = 456
