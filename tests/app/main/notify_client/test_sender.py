from itsdangerous import BadSignature
from pytest import fail

from app.notify_client.sender import generate_token, check_token


def test_should_return_email_from_signed_token(notifications_admin,
                                               notifications_admin_db,
                                               notify_db_session):
    email = 'email@something.com'
    token = generate_token(email)
    assert email == check_token(token)


def test_should_throw_exception_when_token_is_tampered_with(notifications_admin,
                                                            notifications_admin_db,
                                                            notify_db_session):
    email = 'email@something.com'
    token = generate_token(email)
    try:
        check_token(token + 'qerqwer')
        fail()
    except BadSignature:
        pass


def test_return_none_when_token_is_expired(notifications_admin,
                                           notifications_admin_db,
                                           notify_db_session):
    with notifications_admin.test_request_context():
        notifications_admin.config['TOKEN_MAX_AGE_SECONDS'] = -1000
        email = 'email@something.com'
        token = generate_token(email)
        assert check_token(token) is None
        notifications_admin.config['TOKEN_MAX_AGE_SECONDS'] = 120000
