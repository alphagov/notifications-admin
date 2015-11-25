from datetime import datetime

import pytest
import sqlalchemy

from app.models import Users
from app.main.dao import users_dao


def test_insert_user_should_add_user(notifications_admin, notifications_admin_db):
    user = Users(name='test insert',
                 password='somepassword',
                 email_address='test@insert.gov.uk',
                 mobile_number='+441234123412',
                 created_at=datetime.now(),
                 role_id=1)

    users_dao.insert_user(user)
    saved_user = users_dao.get_user_by_id(user.id)
    assert saved_user == user


def test_insert_user_with_role_that_does_not_exist_fails(notifications_admin, notifications_admin_db):
    user = Users(name='test insert',
                 password='somepassword',
                 email_address='test@insert.gov.uk',
                 mobile_number='+441234123412',
                 created_at=datetime.now(),
                 role_id=100)
    with pytest.raises(sqlalchemy.exc.IntegrityError) as error:
        users_dao.insert_user(user)
    assert 'insert or update on table "users" violates foreign key constraint "users_role_id_fkey"' in str(error.value)
