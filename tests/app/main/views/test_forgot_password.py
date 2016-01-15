from flask import url_for
from app.main.dao import users_dao
from tests.app.main import create_test_user


def test_should_render_forgot_password(app_, db_, db_session):
    with app_.test_request_context():
        response = app_.test_client().get(url_for('.forgot_password'))
        assert response.status_code == 200
        assert 'If you have forgotten your password, we can send you an email to create a new password.' \
               in response.get_data(as_text=True)


def test_should_redirect_to_password_reset_sent_and_state_updated(app_,
                                                                  db_,
                                                                  db_session,
                                                                  active_user,
                                                                  mock_send_email):
    with app_.test_request_context():
        response = app_.test_client().post(
            url_for('.forgot_password'),
            data={'email_address': active_user.email_address})
        assert response.status_code == 200
        assert (
            'You have been sent an email containing a link'
            ' to reset your password.') in response.get_data(as_text=True)
        assert users_dao.get_user_by_id(active_user.id).state == 'request_password_reset'
