from itertools import chain

from flask import request, session
from flask_login import AnonymousUserMixin, UserMixin

from app.utils import get_default_sms_sender

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
    return request.view_args.get('service_id', None)


def _get_org_id_from_view_args():
    return request.view_args.get('org_id', None)


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
            return service_id in self._permissions
        if service_id:
            return any(x in self._permissions.get(service_id, []) for x in permissions)

    def has_permission_for_service(self, service_id, permission):
        return permission in self._permissions.get(service_id, [])

    def is_locked(self):
        return self.failed_login_count >= self.max_failed_login_count

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

    def __init__(self, id, service, from_user, email_address, permissions, status, created_at, auth_type):
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
                'auth_type': self.auth_type
                }
        if permissions_as_string:
            data['permissions'] = ','.join(self.permissions)
        else:
            data['permissions'] = sorted(self.permissions)
        return data


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


class Service(dict):

    ALLOWED_PROPERTIES = {
        'active',
        'dvla_organisation',
        'email_branding',
        'email_from',
        'id',
        'inbound_api',
        'letter_contact_block',
        'letter_logo_filename',
        'message_limit',
        'name',
        'organisation_type',
        'permissions',
        'postage',
        'prefix_sms',
        'research_mode',
        'service_callback_api',
    }

    def __init__(self, _dict):
        # in the case of a bad request current service may be `None`
        super().__init__(_dict or {})

    def __getattr__(self, attr):
        if attr in self.ALLOWED_PROPERTIES:
            return self[attr]
        raise AttributeError('`{}` is not a service attribute'.format(attr))

    @property
    def trial_mode(self):
        return self['restricted']

    def has_permission(self, permission):
        return permission in self.permissions

    @property
    def has_jobs(self):
        # Can’t import at top-level because app isn’t yet initialised
        from app import job_api_client
        return job_api_client.has_jobs(self.id)

    @property
    def has_team_members(self):
        from app import user_api_client
        return user_api_client.get_count_of_users_with_permission(
            self.id, 'manage_service'
        ) > 1

    @property
    def has_templates(self):
        from app import service_api_client
        return service_api_client.count_service_templates(
            self.id
        ) > 0

    @property
    def has_email_templates(self):
        from app import service_api_client
        return service_api_client.count_service_templates(
            self.id, template_type='email'
        ) > 0

    @property
    def has_sms_templates(self):
        from app import service_api_client
        return service_api_client.count_service_templates(
            self.id, template_type='sms'
        ) > 0

    @property
    def has_email_reply_to_address(self):
        from app import service_api_client
        return bool(service_api_client.get_reply_to_email_addresses(
            self.id
        ))

    @property
    def needs_to_add_email_reply_to_address(self):
        return self.has_email_templates and not self.has_email_reply_to_address

    @property
    def shouldnt_use_govuk_as_sms_sender(self):
        return self.organisation_type in {'local', 'nhs'}

    @property
    def sms_sender_is_govuk(self):
        from app import service_api_client
        return get_default_sms_sender(
            service_api_client.get_sms_senders(self.id)
        ) in {'GOVUK', 'None'}

    @property
    def needs_to_change_sms_sender(self):
        return all((
            self.has_sms_templates,
            self.shouldnt_use_govuk_as_sms_sender,
            self.sms_sender_is_govuk,
        ))

    @property
    def go_live_checklist_completed(self):
        return all((
            self.has_team_members,
            self.has_templates,
            not self.needs_to_add_email_reply_to_address,
            not self.needs_to_change_sms_sender,
        ))

    @property
    def go_live_checklist_completed_as_yes_no(self):
        return 'Yes' if self.go_live_checklist_completed else 'No'
