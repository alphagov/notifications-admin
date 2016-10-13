from notifications_python_client.notifications import BaseAPIClient
from notifications_python_client.errors import HTTPError

from app.notify_client.models import User


class UserApiClient(BaseAPIClient):
    def __init__(self):
        super().__init__("a", "b", "c")

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.service_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = app.config['ADMIN_CLIENT_SECRET']
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
        user_data = self.get('/user/email', params={'email': email_address})
        return User(user_data['data'], max_failed_login_count=self.max_failed_login_count)

    def get_user_by_email_or_none(self, email_address):
        try:
            return self.get_user_by_email(email_address)
        except HTTPError as e:
            if e.status_code == 404:
                return None

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
        self.post(endpoint, data=data)

    def send_verify_email(self, user_id, to):
        data = {'to': to}
        endpoint = '/user/{0}/email-verification'.format(user_id)
        self.post(endpoint, data=data)

    def send_already_registered_email(self, user_id, to):
        data = {'email': to}
        endpoint = '/user/{0}/email-already-registered'.format(user_id)
        self.post(endpoint, data=data)

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

    def get_users_for_service(self, service_id):
        endpoint = '/service/{}/users'.format(service_id)
        resp = self.get(endpoint)
        return [User(data) for data in resp['data']]

    def add_user_to_service(self, service_id, user_id, permissions):
        endpoint = '/service/{}/users/{}'.format(service_id, user_id)
        data = [{'permission': x} for x in permissions]
        resp = self.post(endpoint, data=data)
        return User(resp['data'], max_failed_login_count=self.max_failed_login_count)

    def set_user_permissions(self, user_id, service_id, permissions):
        data = [{'permission': x} for x in permissions]
        endpoint = '/user/{}/service/{}/permission'.format(user_id, service_id)
        self.post(endpoint, data=data)

    def send_reset_password_url(self, email_address):
        endpoint = '/user/reset-password'
        data = {'email': email_address}
        self.post(endpoint, data=data)

    def is_email_unique(self, email_address):
        if self.get_user_by_email_or_none(email_address):
            return False
        return True

    def activate_user(self, user):
        if user.state == 'pending':
            user.state = 'active'
            return self.update_user(user)
        else:
            return user

    def send_change_email_verification(self, user_id, new_email):
        endpoint = '/user/{}/change-email-verification'.format(user_id)
        data = {'email': new_email}
        self.post(endpoint, data)
