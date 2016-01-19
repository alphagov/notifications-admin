import sqlalchemy
from pytest import fail

from app.main.dao import verify_codes_dao
from app.main.encryption import check_hash


def test_insert_new_code_and_get_it_back(app_, db_, db_session):

    verify_codes_dao.add_code(user_id=1, code='12345', code_type='email')
    saved_codes = verify_codes_dao.get_codes(user_id=1, code_type='email')
    assert len(saved_codes) == 1
    saved_code = saved_codes[0]
    assert saved_code.user_id == 1
    assert check_hash('12345', saved_code.code)
    assert saved_code.code_type == 'email'
    assert saved_code.code_used is False


def test_insert_new_code_should_thrw_exception_when_type_does_not_exist(app_,
                                                                        db_,
                                                                        db_session):
    try:
        verify_codes_dao.add_code(user_id=1, code='23545', code_type='not_real')
        fail('Should have thrown an exception')
    except sqlalchemy.exc.DataError as e:
        assert 'invalid input value for enum verify_code_types: "not_real"' in e.orig.pgerror


def test_should_return_none_if_code_is_used(app_,
                                            db_,
                                            db_session):

    code = verify_codes_dao.add_code(user_id=1, code='12345', code_type='email')
    verify_codes_dao.use_code(code.id)
    saved_code = verify_codes_dao.get_code_by_code(user_id=1, code_type='email', code='12345')
    assert not saved_code
