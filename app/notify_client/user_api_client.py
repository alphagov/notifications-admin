from client.notifications import BaseAPIClient


class UserApiClient(BaseAPIClient):

    def __init__(self, base_url=None, client_id=None, secret=None):
        super(self.__class__, self).__init__(base_url=base_url or 'base_url',
                                             client_id=client_id or 'client_id',
                                             secret=secret or 'secret')

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.client_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.secret = app.config['ADMIN_CLIENT_SECRET']
        self.user_max_failed_login_count = app.config["MAX_FAILED_LOGIN_COUNT"]

    def register_user(self, name, email_address,  mobile_number, password):
        data = {
            "name": name,
            "email_address": email_address,
            "mobile_number": mobile_number,
            "password": password
        }
        user_data = self.post("/user", data)
        return User(user_data, max_failed_login_count=self.user_max_failed_login_count)


class User(object):

    def __init__(self, fields, max_failed_login_count=3):
        self.fields = fields
        self.max_failed_login_count = max_failed_login_count

    @property
    def id(self):
        return self.fields.get('id')

    @property
    def name(self):
        return self.fields.get('name')

    @property
    def email_address(self):
        return self.fields.get('email_address')

    @property
    def mobile_number(self):
        return self.fields.get('mobile_number')

    @property
    def password_changed_at(self):
        return self.fields.get('password_changed_at')

    @property
    def is_authenticated(self):
        return self.fields.get('is_authenticated')

    @property
    def is_active(self):
        if self.fields.get('state') != 'active':
            return False
        else:
            return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_locked(self):
        if self.fields.get('failed_login_count') < self.max_failed_login_count:
            return False
        else:
            return True
