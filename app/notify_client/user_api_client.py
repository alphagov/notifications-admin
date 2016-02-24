from notifications_python_client.notifications import BaseAPIClient
from notifications_python_client.errors import HTTPError

from flask.ext.login import UserMixin


class UserApiClient(BaseAPIClient):
    def __init__(self, base_url=None, client_id=None, secret=None):
        super(self.__class__, self).__init__(base_url=base_url or 'base_url',
                                             client_id=client_id or 'client_id',
                                             secret=secret or 'secret')

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.client_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.secret = app.config['ADMIN_CLIENT_SECRET']
        self.max_failed_login_count = app.config["MAX_FAILED_LOGIN_COUNT"]

    def register_user(self, name, email_address, mobile_number, password):
        data = {
            "name": name,
            "email_address": email_address,
            "mobile_number": mobile_number,
            "password": password
        }
        user_data = self.post("/user", data)
        return User(user_data['data'], max_failed_login_count=self.max_failed_login_count)

    def get_user(self, id):
        url = "/user/{}".format(id)
        user_data = self.get(url)
        return User(user_data['data'], max_failed_login_count=self.max_failed_login_count)

    def get_user_by_email(self, email_address):
        params = {'email': email_address}
        user_data = self.get('/user/email', params=params)
        return User(user_data['data'], max_failed_login_count=self.max_failed_login_count)

    def get_users(self):
        users_data = self.get("/user")['data']
        users = []
        for user in users_data:
            users.append(User(user, max_failed_login_count=self.max_failed_login_count))
        return users

    def update_user(self, user):
        data = user.serialize()
        url = "/user/{}".format(user.id)
        user_data = self.put(url, data=data)
        return User(user_data['data'], max_failed_login_count=self.max_failed_login_count)

    def verify_password(self, user_id, password):
        try:
            url = "/user/{}/verify/password".format(user_id)
            data = {"password": password}
            self.post(url, data=data)
            return True
        except HTTPError as e:
            if e.status_code == 400 or e.status_code == 404:
                return False

    def send_verify_code(self, user_id, code_type, to):
        data = {'to': to}
        endpoint = '/user/{0}/{1}-code'.format(user_id, code_type)
        resp = self.post(endpoint, data=data)

    def check_verify_code(self, user_id, code, code_type):
        data = {'code_type': code_type, 'code': code}
        endpoint = '/user/{}/verify/code'.format(user_id)
        try:
            resp = self.post(endpoint, data=data)
            return True, ''
        except HTTPError as e:
            if e.status_code == 400 or e.status_code == 404:
                if 'Code not found' in e.message:
                    return False, 'Code not found'
                elif 'Code has expired' in e.message:
                    return False, 'Code has expired'
                else:
                    # TODO what is the default message?
                    return False, 'Code not found'
            raise e


class User(UserMixin):
    def __init__(self, fields, max_failed_login_count=3):
        self._id = fields.get('id')
        self._name = fields.get('name')
        self._email_address = fields.get('email_address')
        self._mobile_number = fields.get('mobile_number')
        self._password_changed_at = fields.get('password_changed_at')
        self._permissions = set(fields.get('permissions')) if fields.get('permission') is not None else set()
        self._failed_login_count = 0
        self._state = fields.get('state')
        self.max_failed_login_count = max_failed_login_count

    def get_id(self):
        return self.id

    def is_active(self):
        return self.state == 'active'

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
        if permissions is None:
            permissions = set()
        self._permissions = set(permissions)

    def add_permissions(self, permissions):
        self._permissions.update(permissions)

    def remove_permissions(self, permissions):
        self._permissions -= permissions

    def has_permissions(self, permissions):
        return self._permissions > set(permissions)

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
