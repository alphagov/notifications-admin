from datetime import datetime

import pytest
import sqlalchemy

from app.models import User
from app.main.dao import users_dao


def test_insert_user_should_add_user(notifications_admin, notifications_admin_db):
    user = User(name='test insert',
                password='somepassword',
                email_address='test@insert.gov.uk',
                mobile_number='+441234123412',
                created_at=datetime.now(),
                role_id=1)

    users_dao.insert_user(user)
    saved_user = users_dao.get_user_by_id(user.id)
    assert saved_user == user


def test_insert_user_with_role_that_does_not_exist_fails(notifications_admin, notifications_admin_db):
    user = User(name='role does not exist',
                password='somepassword',
                email_address='test@insert.gov.uk',
                mobile_number='+441234123412',
                created_at=datetime.now(),
                role_id=100)
    with pytest.raises(sqlalchemy.exc.IntegrityError) as error:
        users_dao.insert_user(user)
    assert 'insert or update on table "users" violates foreign key constraint "users_role_id_fkey"' in str(error.value)


def test_get_user_by_email(notifications_admin, notifications_admin_db):
    user = User(name='test_get_by_email',
                password='somepassword',
                email_address='email@example.gov.uk',
                mobile_number='+441234153412',
                created_at=datetime.now(),
                role_id=1)

    users_dao.insert_user(user)
    retrieved = users_dao.get_user_by_email(user.email_address)
    assert retrieved == user


def test_get_all_users_returns_all_users(notifications_admin, notifications_admin_db):
    user1 = User(name='test one',
                 password='somepassword',
                 email_address='test1@get_all.gov.uk',
                 mobile_number='+441234123412',
                 created_at=datetime.now(),
                 role_id=1)
    user2 = User(name='test two',
                 password='some2ndpassword',
                 email_address='test2@get_all.gov.uk',
                 mobile_number='+441234123412',
                 created_at=datetime.now(),
                 role_id=1)
    user3 = User(name='test three',
                 password='some2ndpassword',
                 email_address='test2@get_all.gov.uk',
                 mobile_number='+441234123412',
                 created_at=datetime.now(),
                 role_id=1)

    users_dao.insert_user(user1)
    users_dao.insert_user(user2)
    users_dao.insert_user(user3)
    users = users_dao.get_all_users()
    assert len(users) == 3
    assert users == [user1, user2, user3]
