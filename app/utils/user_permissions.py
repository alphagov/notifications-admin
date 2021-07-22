from itertools import chain

permission_mappings = {
    'send_messages': ['send_texts', 'send_emails', 'send_letters'],
    'manage_templates': ['manage_templates'],
    'manage_service': ['manage_users', 'manage_settings'],
    'manage_api_keys': ['manage_api_keys'],
    'view_activity': ['view_activity'],
    'create_broadcasts': ['create_broadcasts', 'reject_broadcasts', 'cancel_broadcasts'],
    'approve_broadcasts': ['approve_broadcasts', 'reject_broadcasts', 'cancel_broadcasts'],
}

all_ui_permissions = set(permission_mappings.keys())
all_db_permissions = set(chain(*permission_mappings.values()))

permission_options = (
    ('view_activity', 'See dashboard'),
    ('send_messages', 'Send messages'),
    ('manage_templates', 'Add and edit templates'),
    ('manage_service', 'Manage settings, team and usage'),
    ('manage_api_keys', 'Manage API integration'),
)

broadcast_permission_options = (
    ('manage_templates', 'Add and edit templates'),
    ('create_broadcasts', 'Create new alerts'),
    ('approve_broadcasts', 'Approve alerts'),
)


def translate_permissions_from_db_to_ui(db_permissions):
    """
    Given a list of database permissions, return a set of UI permissions

    A UI permission is returned if all of its DB permissions are in the permission list that is passed in.
    Any DB permissions in the list that are not known permissions are also returned.
    """
    unknown_database_permissions = set(db_permissions) - all_db_permissions

    return {
        ui_permission for ui_permission, db_permissions_for_ui_permission in permission_mappings.items()
        if set(db_permissions_for_ui_permission) <= set(db_permissions)
    } | unknown_database_permissions


def translate_permissions_from_ui_to_db(ui_permissions):
    """
    Given a list of UI permissions (ie: checkboxes on a permissions edit page), return a set of DB permissions

    Looks them up in the mapping, falling back to just passing through if they're not recognised.
    """
    return set(chain.from_iterable(
        permission_mappings.get(ui_permission, [ui_permission]) for ui_permission in ui_permissions
    ))
