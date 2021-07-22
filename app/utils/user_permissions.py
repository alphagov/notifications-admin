from itertools import chain

roles = {
    'send_messages': ['send_texts', 'send_emails', 'send_letters'],
    'manage_templates': ['manage_templates'],
    'manage_service': ['manage_users', 'manage_settings'],
    'manage_api_keys': ['manage_api_keys'],
    'view_activity': ['view_activity'],
    'create_broadcasts': ['create_broadcasts', 'reject_broadcasts', 'cancel_broadcasts'],
    'approve_broadcasts': ['approve_broadcasts', 'reject_broadcasts', 'cancel_broadcasts'],
}

all_permissions = set(roles.keys())
all_database_permissions = set(chain(*roles.values()))

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


def translate_permissions_from_db_to_admin_roles(permissions):
    """
    Given a list of database permissions, return a set of roles

    A role is returned if all of its database permissions are in the permission list that is passed in.
    Any permissions in the list that are not database permissions are also returned.
    """
    unknown_database_permissions = {p for p in permissions if p not in all_database_permissions}

    return {
        admin_role for admin_role, db_role_list in roles.items()
        if set(db_role_list) <= set(permissions)
    } | unknown_database_permissions


def translate_permissions_from_admin_roles_to_db(permissions):
    """
    Given a list of admin roles (ie: checkboxes on a permissions edit page for example), return a set of db permissions

    Looks them up in the roles dict, falling back to just passing through if they're not recognised.
    """
    return set(chain.from_iterable(roles.get(permission, [permission]) for permission in permissions))
