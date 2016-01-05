import uuid

from app.main.dao import password_reset_token_dao
from app.models import PasswordResetToken
from tests.app.main import create_test_user


def test_should_insert_and_return_token(notifications_admin, notifications_admin_db, notify_db_session):
    user = create_test_user('active')
    token_id = uuid.uuid4()
    reset_token = PasswordResetToken(token=str(token_id),
                                     user_id=user.id)

    password_reset_token_dao.insert(reset_token)
    saved_token = password_reset_token_dao.get_token(str(token_id))
    assert saved_token.token == str(token_id)
