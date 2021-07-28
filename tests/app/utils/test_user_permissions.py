import pytest

from app.utils.user_permissions import (
    translate_permissions_from_db_to_ui,
    translate_permissions_from_ui_to_db,
)


@pytest.mark.parametrize('db_permissions,expected_ui_permissions', [
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
def test_translate_permissions_from_db_to_ui(
    db_permissions,
    expected_ui_permissions,
):
    ui_permissions = translate_permissions_from_db_to_ui(db_permissions)
    assert ui_permissions == expected_ui_permissions


def test_translate_permissions_from_ui_to_db():
    ui_permissions = ['send_messages', 'manage_templates', 'some_unknown_permission']
    db_permissions = translate_permissions_from_ui_to_db(ui_permissions)

    assert db_permissions == {
        'send_texts', 'send_emails', 'send_letters', 'manage_templates', 'some_unknown_permission'
    }
