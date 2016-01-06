import uuid

from app.main.dao import password_reset_token_dao
from tests.app.main import create_test_user


def test_should_insert_and_return_token(notifications_admin, notifications_admin_db, notify_db_session):
    user = create_test_user('active')
    token_id = str(uuid.uuid4())
    password_reset_token_dao.insert(token=token_id, user_id=user.id)
    saved_token = password_reset_token_dao.get_token(token_id)
    assert saved_token.token == token_id
