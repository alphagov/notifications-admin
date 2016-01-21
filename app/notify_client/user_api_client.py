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
        return User(user_data['data'], max_failed_login_count=self.user_max_failed_login_count)

    def get_user(self, id):
        url = "{}/user/{}".format(self.base_url, id)
        user_data = self.get(url)
        return User(user_data['data'], max_failed_login_count=self.user_max_failed_login_count)

    def update_user(self, user):
        data = user.serialize()
        url = "{}/user/{}".format(self.base_url, user.id)
        user_data = self.put(url, data=data)
        return User(user_data['data'], max_failed_login_count=self.user_max_failed_login_count)


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

    def get_id(self):
        return self.id

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.state == 'active'

    @property
    def state(self):
        return self.fields['state']

    @state.setter
    def state(self, state):
        self.fields['state'] = state

    def is_anonymous(self):
        return False

    def is_locked(self):
        return self.fields.get('failed_login_count') > self.max_failed_login_count

    def serialize(self):
        return self.fields
