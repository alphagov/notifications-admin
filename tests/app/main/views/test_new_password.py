from datetime import datetime, timedelta

from app.main.dao import password_reset_token_dao, users_dao
from app.models import PasswordResetToken
from tests.app.main import create_test_user
from app.main.encryption import check_hash


def test_should_render_new_password_template(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            password_reset_token_dao.insert('some_token', user.id)
        response = client.get('/new-password/some_token')
        assert response.status_code == 200
        assert ' You can now create a new password for your account.' in response.get_data(as_text=True)


def test_should_redirect_to_two_factor_when_password_reset_is_successful(notifications_admin, notifications_admin_db,
                                                                         notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            password_reset_token_dao.insert('some_token', user.id)
        response = client.post('/new-password/some_token',
                               data={'new_password': 'a-new_password'})
        assert response.status_code == 302
        assert response.location == 'http://localhost/two-factor'
        saved_user = users_dao.get_user_by_id(user.id)
        assert check_hash('a-new_password', saved_user.password)


def test_should_return_validation_error_that_token_is_expired(notifications_admin, notifications_admin_db,
                                                              notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            expired_token = PasswordResetToken(id=1, token='some_token', user_id=user.id,
                                               expiry_date=datetime.now() + timedelta(hours=-2))
            password_reset_token_dao.insert_token(expired_token)
        response = client.post('/new-password/some_token',
                               data={'new_password': 'a-new_password'})
        assert response.status_code == 200
        assert 'token is invalid' in response.get_data(as_text=True)
