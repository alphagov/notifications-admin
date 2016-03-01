import json

from notifications_python_client.notifications import BaseAPIClient
from notifications_python_client.errors import HTTPError

from app.notify_client.models import User


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

    def get_users_for_service(self, service_id):
        endpoint = '/service/{}/users'.format(service_id)
        resp = self.get(endpoint)
        return [User(data) for data in resp['data']]

    def add_user_to_service(self, service_id, user_id):
        endpoint = '/service/{}/users/{}'.format(service_id, user_id)
        resp = self.post(endpoint)
        return User(resp['data'], max_failed_login_count=self.max_failed_login_count)
