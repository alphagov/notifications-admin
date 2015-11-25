import pytest
import sqlalchemy

from app.models import Roles
from app.main.dao import roles_dao


def test_insert_role_should_be_able_to_get_role(notifications_admin, notifications_admin_db):
    role = Roles(id=1000, role='some role for test')
    roles_dao.insert_role(role)

    saved_role = roles_dao.get_role_by_id(role.id)
    assert saved_role == role


def test_insert_role_will_throw_error_if_role_already_exists():
    role = Roles(id=1, role='cannot create a duplicate')

    with pytest.raises(sqlalchemy.exc.IntegrityError) as error:
        roles_dao.insert_role(role)
    assert 'duplicate key value violates unique constraint "roles_pkey"' in str(error.value)
