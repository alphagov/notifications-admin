from datetime import datetime
import pytest
import sqlalchemy
from app.main.encryption import check_hash
from app.models import User
from app.main.dao import users_dao


@pytest.mark.skipif(True, reason='Database tests to move to api and ineraction tests done here')
def test_insert_user_should_add_user(db_, db_session):
    user = User(name='test insert',
                password='somepassword',
                email_address='test@insert.gov.uk',
                mobile_number='+441234123412',
                role_id=1)

    users_dao.insert_user(user)
    saved_user = users_dao.get_user_by_id(user.id)
    assert saved_user == user


@pytest.mark.skipif(True, reason='Database tests to move to api and ineraction tests done here')
def test_insert_user_with_role_that_does_not_exist_fails(db_, db_session):
    user = User(name='role does not exist',
                password='somepassword',
                email_address='test@insert.gov.uk',
                mobile_number='+441234123412',
                role_id=100)
    with pytest.raises(sqlalchemy.exc.IntegrityError) as error:
        users_dao.insert_user(user)
    assert 'insert or update on table "users" violates foreign key constraint "users_role_id_fkey"' in str(error.value)


def test_get_user_by_email_calls_api(db_, db_session, mock_active_user, mock_get_user_from_api):
    users_dao.get_user_by_email(mock_active_user.email_address)
    mock_get_user_from_api.assert_called_once_with(mock_active_user.email_address)


def test_get_all_users_calls_api(db_, db_session, mock_get_all_users_from_api):
    users_dao.get_all_users()
    assert mock_get_all_users_from_api.called


def test_user_is_active_is_false_if_state_is_inactive(db_, db_session, mock_active_user):
    assert mock_active_user.is_active() is True
    mock_active_user.state = 'inactive'
    assert mock_active_user.is_active() is False


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


@pytest.mark.skipif(True, reason='Database tests to move to api and ineraction tests done here')
def test_should_throws_error_when_id_does_not_exist(db_, db_session):
    with pytest.raises(AttributeError) as error:
        users_dao.activate_user(123)
    assert '''object has no attribute 'state''''' in str(error.value)


def test_should_update_email_address(db_, db_session, mock_active_user, mock_get_user, mock_update_user_email_api):
    assert mock_active_user.email_address == 'test@user.gov.uk'
    users_dao.update_email_address(mock_active_user.id, 'new_email@testit.gov.uk')

    assert mock_active_user.email_address == 'new_email@testit.gov.uk'
    mock_update_user_email_api.assert_called_once_with(mock_active_user)


@pytest.mark.skipif(True, reason='Database tests to move to api and ineraction tests done here')
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


@pytest.mark.skipif(True, reason='Database tests to move to api and ineraction tests done here')
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


@pytest.mark.skipif(True, reason='Database tests to move to api and ineraction tests done here')
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
