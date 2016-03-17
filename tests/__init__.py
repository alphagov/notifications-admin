import pytest
from flask.testing import FlaskClient
from flask import url_for


class TestClient(FlaskClient):
    def login(self, user):
        # Skipping authentication here and just log them in
        with self.session_transaction() as session:
            session['user_details'] = {
                "email": user.email_address,
                "id": user.id}
        # Include mock_login fixture in test for this to work.
        # TODO would be better for it to be mocked in this
        # function
        response = self.post(
            url_for('main.two_factor'), data={'sms_code': '12345'})
        assert response.status_code == 302

    def logout(self, user):
        self.get(url_for("main.logout"))


def service_json(id_, name, users, limit=1000, active=False, restricted=True):
    return {
        'id': id_,
        'name': name,
        'users': users,
        'limit': limit,
        'active': active,
        'restricted': restricted
    }


def template_json(id_, name, type_, content, service_id):
    return {
        'id': id_,
        'name': name,
        'template_type': type_,
        'content': content,
        'service': service_id
    }


def api_key_json(id_, name, expiry_date=None):
    return {'id': id_,
            'name': name,
            'expiry_date': expiry_date
            }


def invite_json(id, from_user, service_id, email_address, permissions, created_at, status):
    return {'id': id,
            'from_user': from_user,
            'service': service_id,
            'email_address': email_address,
            'status': status,
            'permissions': permissions,
            'created_at': created_at
            }


TEST_USER_EMAIL = 'test@user.gov.uk'


def create_test_user(state):
    from app.main.dao import users_dao
    user = None
    users_dao.insert_user(user)
    return user


def create_test_api_user(state, permissions={}):
    from app.notify_client.user_api_client import User
    user_data = {'id': 1,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': TEST_USER_EMAIL,
                 'mobile_number': '+441234123412',
                 'state': state,
                 'permissions': permissions
                 }
    user = User(user_data)
    return user


def create_another_test_user(state):
    from app.main.dao import users_dao
    user = None
    users_dao.insert_user(user)
    return user


def get_test_user():
    from app.main.dao import users_dao
    return users_dao.get_user_by_email(TEST_USER_EMAIL)


def job_json():
    import uuid
    import datetime
    uuid.uuid4()
    job_id = str(uuid.uuid4())
    created_at = str(datetime.datetime.now().time())
    data = {
        'id': str(job_id),
        'service': 1,
        'template': 1,
        'original_file_name': 'thisisatest.csv',
        'bucket_name': 'service-1-{}-notify'.format(job_id),
        'file_name': '{}.csv'.format(job_id),
        'created_at': created_at,
        'notification_count': 1,
        'notifications_sent': 1,
        'status': ''
        }
    return data


def notification_json():
    import datetime
    data = {
        'notifications': [{
            'sent_at': str(datetime.datetime.now().time())
        } for i in range(5)],
        'links': {}
    }
    return data


def validate_route_permission(mocker,
                              app_,
                              method,
                              response_code,
                              route,
                              permissions,
                              usr,
                              service):
    usr._permissions[str(service['id'])] = permissions
    mocker.patch(
        'app.user_api_client.check_verify_code',
        return_value=(True, ''))
    mocker.patch(
        'app.service_api_client.get_services',
        return_value={'data': []})
    mocker.patch('app.user_api_client.get_user', return_value=usr)
    mocker.patch('app.user_api_client.get_user_by_email', return_value=usr)
    mocker.patch('app.service_api_client.get_service', return_value={'data': service})

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(usr)
            resp = None
            with client.session_transaction() as session:
                session['service_id'] = str(service['id'])
            if method == 'GET':
                resp = client.get(route)
            elif method == 'POST':
                resp = client.post(route)
            else:
                pytest.fail("Invalid method call {}".format(method))
            if resp.status_code != response_code:
                pytest.fail("Invalid permissions set for endpoint {}".format(route))
    return resp
