import pytest
from flask.testing import FlaskClient
from flask import url_for
from flask_login import login_user


class TestClient(FlaskClient):
    def login(self, user, mocker=None, service=None):
        # Skipping authentication here and just log them in
        with self.session_transaction() as session:
            session['user_id'] = user.id
            session['_fresh'] = True
        if mocker:
            mocker.patch('app.user_api_client.get_user', return_value=user)
        if mocker and service:
            mocker.patch('app.service_api_client.get_service', return_value={'data': service})
        login_user(user, remember=True)

    def login_fresh(self):
        return True

    def logout(self, user):
        self.get(url_for("main.logout"))


def service_json(id_, name, users, limit=1000, active=False, restricted=True, email_from=None):
    return {
        'id': id_,
        'name': name,
        'users': users,
        'limit': limit,
        'active': active,
        'restricted': restricted,
        'email_from': email_from
    }


def template_json(service_id, id_=1, name="sample template", type_="sms", content="template content"):
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
        'created_at': created_at,
        'notification_count': 1,
        'notifications_sent': 1,
        'status': ''
        }
    return data


def notification_json(service_id,
                      job=None,
                      template=None,
                      to='07123456789',
                      status='sent',
                      sent_at=None,
                      created_at=None,
                      with_links=False):
    import datetime
    if job is None:
        job = job_json()
    if template is None:
        template = template_json(service_id)
    if sent_at is None:
        sent_at = str(datetime.datetime.now().time())
    if created_at is None:
        created_at = str(datetime.datetime.now().time())
    links = {}
    if with_links:
        links = {
            'prev': '/service/{}/notifications'.format(service_id),
            'next': '/service/{}/notifications'.format(service_id),
            'last': '/service/{}/notifications'.format(service_id)
        }
    data = {
        'notifications': [{
            'to': to,
            'template': {
                'id': template['id'],
                'name': template['name'],
                'template_type': template['template_type']},
            'job': {'id': job['id'], 'original_file_name': job['original_file_name']},
            'sent_at': sent_at,
            'status': status,
            'created_at': created_at
        } for i in range(5)],
        'links': links
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
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[usr])
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(usr)
            resp = None
            if method == 'GET':
                resp = client.get(route)
            elif method == 'POST':
                resp = client.post(route)
            else:
                pytest.fail("Invalid method call {}".format(method))
            if resp.status_code != response_code:
                pytest.fail("Invalid permissions set for endpoint {}".format(route))
    return resp
