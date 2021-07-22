import pytest

from app.utils.user_permissions import (
    translate_permissions_from_admin_roles_to_db,
    translate_permissions_from_db_to_admin_roles,
)


@pytest.mark.parametrize('db_roles,admin_roles', [
    (
        ['approve_broadcasts', 'reject_broadcasts', 'cancel_broadcasts'],
        {'approve_broadcasts'},
    ),
    (
        ['manage_templates', 'create_broadcasts', 'reject_broadcasts', 'cancel_broadcasts'],
        {'create_broadcasts', 'manage_templates'},
    ),
    (
        ['manage_templates'],
        {'manage_templates'},
    ),
    (
        ['create_broadcasts'],
        set(),
    ),
    (
        ['send_texts', 'send_emails', 'send_letters', 'manage_templates', 'some_unknown_permission'],
        {'send_messages', 'manage_templates', 'some_unknown_permission'},
    ),
])
def test_translate_permissions_from_db_to_admin_roles(
    db_roles,
    admin_roles,
):
    roles = translate_permissions_from_db_to_admin_roles(db_roles)
    assert roles == admin_roles


def test_translate_permissions_from_admin_roles_to_db():
    roles = ['send_messages', 'manage_templates', 'some_unknown_permission']
    db_perms = translate_permissions_from_admin_roles_to_db(roles)
    assert db_perms == {'send_texts', 'send_emails', 'send_letters', 'manage_templates', 'some_unknown_permission'}
