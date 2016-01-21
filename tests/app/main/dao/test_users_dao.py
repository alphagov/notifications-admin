from datetime import datetime
import pytest
import sqlalchemy
from app.main.encryption import check_hash
from app.models import User
from app.main.dao import users_dao


@pytest.mark.xfail(reason='Tests will be moved to api')
def test_insert_user_should_add_user(db_, db_session):
    user = User(name='test insert',
                password='somepassword',
                email_address='test@insert.gov.uk',
                mobile_number='+441234123412',
                role_id=1)

    users_dao.insert_user(user)
    saved_user = users_dao.get_user_by_id(user.id)
    assert saved_user == user


@pytest.mark.xfail(reason='Tests will be moved to api')
def test_insert_user_with_role_that_does_not_exist_fails(db_, db_session):
    user = User(name='role does not exist',
                password='somepassword',
                email_address='test@insert.gov.uk',
                mobile_number='+441234123412',
                role_id=100)
    with pytest.raises(sqlalchemy.exc.IntegrityError) as error:
        users_dao.insert_user(user)
    assert 'insert or update on table "users" violates foreign key constraint "users_role_id_fkey"' in str(error.value)


@pytest.mark.xfail(reason='Not implemented yet on api client')
def test_get_user_by_email(db_, db_session):
    user = User(name='test_get_by_email',
                password='somepassword',
                email_address='email@example.gov.uk',
                mobile_number='+441234153412',
                role_id=1)

    users_dao.insert_user(user)
    retrieved = users_dao.get_user_by_email(user.email_address)
    assert retrieved == user


@pytest.mark.xfail(reason='Not implemented yet on api client')
def test_get_all_users_returns_all_users(db_, db_session):
    user1 = User(name='test one',
                 password='somepassword',
                 email_address='test1@get_all.gov.uk',
                 mobile_number='+441234123412',
                 role_id=1)
    user2 = User(name='test two',
                 password='some2ndpassword',
                 email_address='test2@get_all.gov.uk',
                 mobile_number='+441234123412',
                 role_id=1)
    user3 = User(name='test three',
                 password='some2ndpassword',
                 email_address='test3@get_all.gov.uk',
                 mobile_number='+441234123412',
                 role_id=1)

    users_dao.insert_user(user1)
    users_dao.insert_user(user2)
    users_dao.insert_user(user3)
    users = users_dao.get_all_users()
    assert len(users) == 3
    assert users == [user1, user2, user3]


@pytest.mark.xfail(reason='Not implemented yet on api client')
def test_increment_failed_lockout_count_should_increade_count_by_1(db_, db_session):
    user = User(name='cannot remember password',
                password='somepassword',
                email_address='test1@get_all.gov.uk',
                mobile_number='+441234123412',
                role_id=1)
    users_dao.insert_user(user)

    savedUser = users_dao.get_user_by_id(user.id)
    assert savedUser.failed_login_count == 0
    users_dao.increment_failed_login_count(user.id)
    assert users_dao.get_user_by_id(user.id).failed_login_count == 1


@pytest.mark.xfail(reason='Not implemented yet on api client')
def test_user_is_locked_if_failed_login_count_is_10_or_greater(db_, db_session):
    user = User(name='cannot remember password',
                password='somepassword',
                email_address='test1@get_all.gov.uk',
                mobile_number='+441234123412',
                role_id=1)
    users_dao.insert_user(user)
    saved_user = users_dao.get_user_by_id(user.id)
    assert saved_user.is_locked() is False

    for _ in range(10):
        users_dao.increment_failed_login_count(user.id)

    saved_user = users_dao.get_user_by_id(user.id)
    assert saved_user.failed_login_count == 10
    assert saved_user.is_locked() is True


@pytest.mark.xfail(reason='Not implemented yet on api client')
def test_user_is_active_is_false_if_state_is_inactive(db_, db_session):
    user = User(name='inactive user',
                password='somepassword',
                email_address='test1@get_all.gov.uk',
                mobile_number='+441234123412',
                role_id=1,
                state='inactive')
    users_dao.insert_user(user)

    saved_user = users_dao.get_user_by_id(user.id)
    assert saved_user.is_active() is False


def test_should_update_user_to_active(mock_activate_user):
    from app.notify_client.user_api_client import User
    user_data = {'name': 'Make user active',
                 'password': 'somepassword',
                 'email_address': 'activate@user.gov.uk',
                 'mobile_number': '+441234123412',
                 'state': 'pending'
                 }
    user = User(user_data)
    activated_user = users_dao.activate_user(user)
    assert activated_user.state == 'active'


@pytest.mark.xfail(reason='Not implemented yet on api client')
def test_should_throws_error_when_id_does_not_exist(db_, db_session):
    with pytest.raises(AttributeError) as error:
        users_dao.activate_user(123)
    assert '''object has no attribute 'state''''' in str(error.value)


@pytest.mark.xfail(reason='Not implemented yet on api client')
def test_should_update_email_address(db_, db_session):
    user = User(name='Update Email',
                password='somepassword',
                email_address='test@it.gov.uk',
                mobile_number='+441234123412',
                role_id=1,
                state='inactive')
    users_dao.insert_user(user)

    saved = users_dao.get_user_by_id(user.id)
    assert saved.email_address == 'test@it.gov.uk'
    users_dao.update_email_address(user.id, 'new_email@testit.gov.uk')
    updated = users_dao.get_user_by_id(user.id)
    assert updated.email_address == 'new_email@testit.gov.uk'


@pytest.mark.xfail(reason='Not implemented yet on api client')
def test_should_update_password(db_, db_session):
    user = User(name='Update Email',
                password='somepassword',
                email_address='test@it.gov.uk',
                mobile_number='+441234123412',
                role_id=1,
                state='active')
    start = datetime.now()
    users_dao.insert_user(user)

    saved = users_dao.get_user_by_id(user.id)
    assert check_hash('somepassword', saved.password)
    assert saved.password_changed_at is None
    users_dao.update_password(saved, 'newpassword')
    updated = users_dao.get_user_by_id(user.id)
    assert check_hash('newpassword', updated.password)
    assert updated.password_changed_at < datetime.now()
    assert updated.password_changed_at > start


@pytest.mark.xfail(reason='Not implemented yet on api client')
def test_should_return_list_of_all_email_addresses(db_, db_session):
    first = User(name='First Person',
                 password='somepassword',
                 email_address='first@it.gov.uk',
                 mobile_number='+441234123412',
                 role_id=1,
                 state='active')
    second = User(name='Second Person',
                  password='somepassword',
                  email_address='second@it.gov.uk',
                  mobile_number='+441234123412',
                  role_id=1,
                  state='active')
    users_dao.insert_user(first)
    users_dao.insert_user(second)

    email_addresses = users_dao.get_all_users()
    expected = [first.email_address, second.email_address]
    assert expected == [x.email_address for x in email_addresses]


@pytest.mark.xfail(reason='Not implemented yet on api client')
def test_should_update_state_to_request_password_reset(db_, db_session):
    user = User(name='Requesting Password Resest',
                password='somepassword',
                email_address='request@new_password.gov.uk',
                mobile_number='+441234123412',
                role_id=1,
                state='active')
    users_dao.insert_user(user)
    users_dao.request_password_reset(user.email_address)
    saved = users_dao.get_user_by_email(user.email_address)
    assert saved.state == 'request_password_reset'
