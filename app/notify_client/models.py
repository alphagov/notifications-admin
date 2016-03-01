from flask.ext.login import (UserMixin, login_fresh)


class User(UserMixin):
    def __init__(self, fields, max_failed_login_count=3):
        self._id = fields.get('id')
        self._name = fields.get('name')
        self._email_address = fields.get('email_address')
        self._mobile_number = fields.get('mobile_number')
        self._password_changed_at = fields.get('password_changed_at')
        self._permissions = fields.get('permissions')
        self._failed_login_count = 0
        self._state = fields.get('state')
        self.max_failed_login_count = max_failed_login_count

    def get_id(self):
        return self.id

    def is_active(self):
        return self.state == 'active'

    def is_authenticated(self):
        # To handle remember me token renewal
        if not login_fresh():
            return False
        return super(User, self).is_authenticated()

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

    def has_permissions(self, service_id, permissions, or_=False):
        if service_id in self._permissions:
            if or_:
                return any([x in self._permissions[service_id] for x in permissions])
            return set(self._permissions[service_id]) > set(permissions)
        return False

    @property
    def failed_login_count(self):
        return self._failed_login_count

    @failed_login_count.setter
    def failed_login_count(self, num):
        self._failed_login_count += num

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
