import sqlalchemy
from pytest import fail

from app.main.dao import verify_codes_dao
from app.main.encryption import check_hash
from tests.app.main import create_test_user


def test_insert_new_code_and_get_it_back(notifications_admin, notifications_admin_db, notify_db_session):
    user = create_test_user()

    verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='email')
    saved_code = verify_codes_dao.get_code(user_id=user.id, code_type='email')
    assert saved_code.user_id == user.id
    assert check_hash('12345', saved_code.code)
    assert saved_code.code_type == 'email'
    assert saved_code.code_used is False


def test_insert_new_code_should_thrw_exception_when_type_does_not_exist(notifications_admin,
                                                                        notifications_admin_db,
                                                                        notify_db_session):
    user = create_test_user()
    try:
        verify_codes_dao.add_code(user_id=user.id, code='23545', code_type='not_real')
        fail('Should have thrown an exception')
    except sqlalchemy.exc.DataError as e:
        assert 'invalid input value for enum verify_code_types: "not_real"' in e.orig.pgerror


def test_should_throw_exception_when_user_does_not_exist(notifications_admin,
                                                         notifications_admin_db,
                                                         notify_db_session):
    try:
        verify_codes_dao.add_code(user_id=1, code='12345', code_type='email')
        fail('Should throw exception')
    except sqlalchemy.exc.IntegrityError as e:
        assert 'ERROR:  insert or update on table "verify_codes" violates ' \
               'foreign key constraint "verify_codes_user_id_fkey"' in e.orig.pgerror


def test_should_return_none_if_code_is_used(notifications_admin,
                                            notifications_admin_db,
                                            notify_db_session):
    user = create_test_user()

    verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='email')
    verify_codes_dao.use_code(user_id=user.id, code='12345', code_type='email')
    saved_code = verify_codes_dao.get_code_by_code(user_id=user.id, code_type='email', code='12345')
    assert saved_code.code_used is True


def test_should_return_none_if_code_is_used(notifications_admin,
                                            notifications_admin_db,
                                            notify_db_session):
    user = create_test_user()

    verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
    code = verify_codes_dao.get_code(user_id=user.id, code_type='sms')
    verify_codes_dao.use_code(code.id)
    code = verify_codes_dao.get_code(user_id=user.id, code_type='sms')
    assert code is None
