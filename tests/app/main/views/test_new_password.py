from pytest import fail

from app.main.dao import users_dao
from app.main.encryption import check_hash
from app.main.exceptions import NoDataFoundException
from app.main.views import generate_token
from tests.app.main import create_test_user


def test_should_render_new_password_template(notifications_admin, notifications_admin_db, notify_db_session):
    response = notifications_admin.test_client().get('/new-password/some_token')
    assert response.status_code == 200
    assert ' You can now create a new password for your account.' in response.get_data(as_text=True)


def test_should_redirect_to_two_factor_when_password_reset_is_successful(notifications_admin,
                                                                         notifications_admin_db,
                                                                         notify_db_session,
                                                                         mocker):
    _set_up_mocker(mocker)
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            token = generate_token(user.email_address)
        response = client.post('/new-password/{}'.format(token),
                               data={'new_password': 'a-new_password'})
        assert response.status_code == 302
        assert response.location == 'http://localhost/two-factor'
        saved_user = users_dao.get_user_by_id(user.id)
        assert check_hash('a-new_password', saved_user.password)


def test_should_redirect_to_forgot_password_with_flash_message_when_token_is_expired(notifications_admin,
                                                                                     notifications_admin_db,
                                                                                     notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            notifications_admin.config['TOKEN_MAX_AGE_SECONDS'] = -1000
            user = create_test_user('active')
            token = generate_token(user.email_address)
        response = client.post('/new-password/{}'.format(token),
                               data={'new_password': 'a-new_password'})
        assert response.status_code == 302
        assert response.location == 'http://localhost/forgot-password'
        notifications_admin.config['TOKEN_MAX_AGE_SECONDS'] = 86400


def test_should_return_raise_no_data_found_exception_when_email_address_does_not_exist(notifications_admin,
                                                                                       notifications_admin_db,
                                                                                       notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            token = generate_token('doesnotexist@it.gov.uk')
            try:
                client.post('/new-password/{}'.format(token),
                            data={'new_password': 'a-new_password'})
                fail('Expected NoDataFoundException')
            except NoDataFoundException:
                pass


def _set_up_mocker(mocker):
    mocker.patch("app.admin_api_client.send_sms")
