from itertools import chain

from flask import abort, request, session
from flask_login import AnonymousUserMixin, UserMixin
from werkzeug.utils import cached_property

from app.models.organisation import Organisation
from app.notify_client.organisations_api_client import organisations_client
from app.utils import is_gov_user

roles = {
    'send_messages': ['send_texts', 'send_emails', 'send_letters'],
    'manage_templates': ['manage_templates'],
    'manage_service': ['manage_users', 'manage_settings'],
    'manage_api_keys': ['manage_api_keys'],
    'view_activity': ['view_activity'],
}

# same dict as above, but flipped round
roles_by_permission = {
    permission: next(
        role for role, permissions in roles.items() if permission in permissions
    ) for permission in chain(*list(roles.values()))
}

all_permissions = set(roles_by_permission.values())

permissions = (
    ('view_activity', 'See dashboard'),
    ('send_messages', 'Send messages'),
    ('manage_templates', 'Add and edit templates'),
    ('manage_service', 'Manage settings, team and usage'),
    ('manage_api_keys', 'Manage API integration'),
)


def _get_service_id_from_view_args():
    return str(request.view_args.get('service_id', '')) or None


def _get_org_id_from_view_args():
    return str(request.view_args.get('org_id', '')) or None


def translate_permissions_from_db_to_admin_roles(permissions):
    """
    Given a list of database permissions, return a set of roles

    look them up in roles_by_permission, falling back to just passing through from the api if they aren't in the dict
    """
    return {roles_by_permission.get(permission, permission) for permission in permissions}


def translate_permissions_from_admin_roles_to_db(permissions):
    """
    Given a list of admin roles (ie: checkboxes on a permissions edit page for example), return a set of db permissions

    Looks them up in the roles dict, falling back to just passing through if they're not recognised.
    """
    return set(chain.from_iterable(roles.get(permission, [permission]) for permission in permissions))


class User(UserMixin):
    def __init__(self, fields, max_failed_login_count=3):
        self.id = fields.get('id')
        self.name = fields.get('name')
        self.email_address = fields.get('email_address')
        self.mobile_number = fields.get('mobile_number')
        self.password_changed_at = fields.get('password_changed_at')
        self._set_permissions(fields.get('permissions', {}))
        self.auth_type = fields.get('auth_type')
        self.failed_login_count = fields.get('failed_login_count')
        self.state = fields.get('state')
        self.max_failed_login_count = max_failed_login_count
        self.logged_in_at = fields.get('logged_in_at')
        self.platform_admin = fields.get('platform_admin')
        self.current_session_id = fields.get('current_session_id')
        self.services = fields.get('services', [])
        self.organisations = fields.get('organisations', [])

    def _set_permissions(self, permissions_by_service):
        """
        Permissions is a dict {'service_id': ['permission a', 'permission b', 'permission c']}

        The api currently returns some granular permissions that we don't set or use separately (but may want
        to in the future):
        * send_texts, send_letters and send_emails become send_messages
        * manage_user and manage_settings become
        users either have all three permissions for a service or none of them, they're not helpful to distinguish
        between on the front end. So lets collapse them into "send_messages" and "manage_service". If we want to split
        them out later, we'll need to rework this function.
        """
        self._permissions = {
            service: translate_permissions_from_db_to_admin_roles(permissions)
            for service, permissions
            in permissions_by_service.items()
        }

    def get_id(self):
        return self.id

    def logged_in_elsewhere(self):
        # if the current user (ie: db object) has no session, they've never logged in before
        return self.current_session_id is not None and session.get('current_session_id') != self.current_session_id

    @property
    def is_active(self):
        return self.state == 'active'

    @property
    def is_gov_user(self):
        return is_gov_user(self.email_address)

    @property
    def is_authenticated(self):
        return (
            not self.logged_in_elsewhere() and
            super(User, self).is_authenticated
        )

    @property
    def permissions(self):
        return self._permissions

    @permissions.setter
    def permissions(self, permissions):
        raise AttributeError("Read only property")

    def has_permissions(self, *permissions, restrict_admin_usage=False):
        unknown_permissions = set(permissions) - all_permissions
        if unknown_permissions:
            raise TypeError('{} are not valid permissions'.format(list(unknown_permissions)))

        # Service id is always set on the request for service specific views.
        service_id = _get_service_id_from_view_args()
        org_id = _get_org_id_from_view_args()

        if not service_id and not org_id:
            # we shouldn't have any pages that require permissions, but don't specify a service or organisation.
            # use @user_is_platform_admin for platform admin only pages
            raise NotImplementedError

        # platform admins should be able to do most things (except eg send messages, or create api keys)
        if self.platform_admin and not restrict_admin_usage:
            return True

        if org_id:
            return org_id in self.organisations
        if not permissions:
            return service_id in self.services
        if service_id:
            return any(x in self._permissions.get(service_id, []) for x in permissions)

    def has_permission_for_service(self, service_id, permission):
        return permission in self._permissions.get(service_id, [])

    def has_template_folder_permission(self, template_folder, service=None):
        from app import current_service

        if service is None:
            service = current_service

        if not service.has_permission('edit_folder_permissions'):
            return True

        if self.platform_admin:
            return True

        # Top-level templates are always visible
        if template_folder is None or template_folder['id'] is None:
            return True

        return self.id in template_folder.get("users_with_permission", [])

    def template_folders_for_service(self, service=None):
        """
        Returns list of template folders that a user can view for a given service
        """
        if not service.has_permission('edit_folder_permissions'):
            return service.all_template_folders

        return [
            template_folder
            for template_folder in service.all_template_folders
            if self.id in template_folder.get("users_with_permission", [])
        ]

    def belongs_to_service(self, service_id):
        return str(service_id) in self.services

    def belongs_to_service_or_403(self, service_id):
        if not self.belongs_to_service(service_id):
            abort(403)

    def is_locked(self):
        return self.failed_login_count >= self.max_failed_login_count

    @property
    def email_domain(self):
        return self.email_address.split('@')[-1]

    @cached_property
    def default_organisation(self):
        return Organisation(
            organisations_client.get_organisation_by_domain(self.email_domain)
        )

    @property
    def default_organisation_type(self):
        if self.default_organisation:
            return self.default_organisation.organisation_type
        if self.has_nhs_email_address:
            return 'nhs'
        return None

    @property
    def has_nhs_email_address(self):
        return self.email_address.lower().endswith((
            '@nhs.uk', '.nhs.uk', '@nhs.net', '.nhs.net',
        ))

    def serialize(self):
        dct = {
            "id": self.id,
            "name": self.name,
            "email_address": self.email_address,
            "mobile_number": self.mobile_number,
            "password_changed_at": self.password_changed_at,
            "state": self.state,
            "failed_login_count": self.failed_login_count,
            "permissions": [x for x in self._permissions],
            "organisations": self.organisations,
            "current_session_id": self.current_session_id
        }
        if hasattr(self, '_password'):
            dct['password'] = self._password
        return dct

    def set_password(self, pwd):
        self._password = pwd


class InvitedUser(object):

    def __init__(self,
                 id,
                 service,
                 from_user,
                 email_address,
                 permissions,
                 status,
                 created_at,
                 auth_type,
                 folder_permissions):
        self.id = id
        self.service = str(service)
        self.from_user = from_user
        self.email_address = email_address
        if isinstance(permissions, list):
            self.permissions = permissions
        else:
            if permissions:
                self.permissions = permissions.split(',')
            else:
                self.permissions = []
        self.status = status
        self.created_at = created_at
        self.auth_type = auth_type
        self.permissions = translate_permissions_from_db_to_admin_roles(self.permissions)
        self.folder_permissions = folder_permissions

    def has_permissions(self, *permissions):
        if self.status == 'cancelled':
            return False
        return set(self.permissions) > set(permissions)

    def has_permission_for_service(self, service_id, permission):
        if self.status == 'cancelled':
            return False
        return self.service == service_id and permission in self.permissions

    def __eq__(self, other):
        return ((self.id,
                self.service,
                self.from_user,
                self.email_address,
                self.auth_type,
                self.status) == (other.id,
                other.service,
                other.from_user,
                other.email_address,
                other.auth_type,
                other.status))

    def serialize(self, permissions_as_string=False):
        data = {'id': self.id,
                'service': self.service,
                'from_user': self.from_user,
                'email_address': self.email_address,
                'status': self.status,
                'created_at': str(self.created_at),
                'auth_type': self.auth_type,
                'folder_permissions': self.folder_permissions
                }
        if permissions_as_string:
            data['permissions'] = ','.join(self.permissions)
        else:
            data['permissions'] = sorted(self.permissions)
        return data

    def template_folders_for_service(self, service=None):
        # only used on the manage users page to display the count, so okay to not be fully fledged for now
        return [{'id': x} for x in self.folder_permissions]


class InvitedOrgUser(object):

    def __init__(self, id, organisation, invited_by, email_address, status, created_at):
        self.id = id
        self.organisation = str(organisation)
        self.invited_by = invited_by
        self.email_address = email_address
        self.status = status
        self.created_at = created_at

    def __eq__(self, other):
        return ((self.id,
                self.organisation,
                self.invited_by,
                self.email_address,
                self.status) == (other.id,
                other.organisation,
                other.invited_by,
                other.email_address,
                other.status))

    def serialize(self, permissions_as_string=False):
        data = {'id': self.id,
                'organisation': self.organisation,
                'invited_by': self.invited_by,
                'email_address': self.email_address,
                'status': self.status,
                'created_at': str(self.created_at)
                }
        return data


class AnonymousUser(AnonymousUserMixin):
    # set the anonymous user so that if a new browser hits us we don't error http://stackoverflow.com/a/19275188
    def logged_in_elsewhere(self):
        return False

    @property
    def default_organisation(self):
        return Organisation(None)
