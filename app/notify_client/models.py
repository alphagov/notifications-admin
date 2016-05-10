from flask.ext.login import (UserMixin, login_fresh)


class User(UserMixin):
    def __init__(self, fields, max_failed_login_count=3):
        self._id = fields.get('id')
        self._name = fields.get('name')
        self._email_address = fields.get('email_address')
        self._mobile_number = fields.get('mobile_number')
        self._password_changed_at = fields.get('password_changed_at')
        self._permissions = fields.get('permissions')
        self._failed_login_count = fields.get('failed_login_count')
        self._state = fields.get('state')
        self.max_failed_login_count = max_failed_login_count
        self.platform_admin = fields.get('platform_admin')

    def get_id(self):
        return self.id

    @property
    def is_active(self):
        return self.state == 'active'

    @property
    def is_authenticated(self):
        # To handle remember me token renewal
        if not login_fresh():
            return False
        return super(User, self).is_authenticated

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, id):
        self._id = id

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def email_address(self):
        return self._email_address

    @email_address.setter
    def email_address(self, email_address):
        self._email_address = email_address

    @property
    def mobile_number(self):
        return self._mobile_number

    @mobile_number.setter
    def mobile_number(self, mobile_number):
        self._mobile_number = mobile_number

    @property
    def password_changed_at(self):
        return self._password_changed_at

    @password_changed_at.setter
    def password_changed_at(self, password_changed_at):
        self._password_changed_at = password_changed_at

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state

    @property
    def permissions(self):
        return self._permissions

    @permissions.setter
    def permissions(self, permissions):
        raise AttributeError("Read only property")

    def has_permissions(self, permissions=[], any_=False, admin_override=False):
        # Only available to the platform admin user
        if admin_override and self.platform_admin:
            return True
        # Not available to the non platform admin users.
        # For example the list all-services page is only available to platform admin users and is not service specific
        if admin_override and not permissions:
            return False

        from flask import request
        # Service id is always set on the request for service specific views.
        service_id = request.view_args.get('service_id', None)
        if service_id in self._permissions:
            if any_:
                return any([x in self._permissions[service_id] for x in permissions])
            return set(self._permissions[service_id]) >= set(permissions)
        return False

    @property
    def failed_login_count(self):
        return self._failed_login_count

    @failed_login_count.setter
    def failed_login_count(self, num):
        self._failed_login_count += num

    def reset_failed_login_count(self):
        self._failed_login_count = 0

    def is_locked(self):
        return self.failed_login_count >= self.max_failed_login_count

    def serialize(self):
        dct = {"id": self.id,
               "name": self.name,
               "email_address": self.email_address,
               "mobile_number": self.mobile_number,
               "password_changed_at": self.password_changed_at,
               "state": self.state,
               "failed_login_count": self.failed_login_count,
               "permissions": [x for x in self._permissions]}
        if getattr(self, '_password', None):
            dct['password'] = self._password
        return dct

    def set_password(self, pwd):
        self._password = pwd


class InvitedUser(object):

    def __init__(self, id, service, from_user, email_address, permissions, status, created_at):
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

    def has_permissions(self, permissions):
        return set(self.permissions) > set(permissions)

    def __eq__(self, other):
        return ((self.id,
                self.service,
                self.from_user,
                self.email_address,
                self.status) == (other.id,
                other.service,
                other.from_user,
                other.email_address,
                other.status))

    def serialize(self, permissions_as_string=False):
        data = {'id': self.id,
                'service': self.service,
                'from_user': self.from_user,
                'email_address': self.email_address,
                'status': self.status,
                'created_at': str(self.created_at)
                }
        if permissions_as_string:
            data['permissions'] = ','.join(self.permissions)
        else:
            data['permissions'] = self.permissions
        return data
