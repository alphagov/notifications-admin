import pytest
import uuid
from datetime import datetime, timedelta, date, timezone
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
            mocker.patch('app.events_api_client.create_event')
        if mocker and service:
            session['service_id'] = service['id']
            mocker.patch('app.service_api_client.get_service', return_value={'data': service})
        login_user(user, remember=True)

    def login_fresh(self):
        return True

    def logout(self, user):
        self.get(url_for("main.logout"))


def sample_uuid():
    return "6ce466d0-fd6a-11e5-82f5-e0accb9d11a6"


def generate_uuid():
    return uuid.uuid4()


def created_by_json(id_, name='', email_address=''):
    return {'id': id_, 'name': name, 'email_address': email_address}


def service_json(
    id_,
    name,
    users,
    message_limit=1000,
    active=False,
    restricted=True,
    email_from=None,
    reply_to_email_address=None,
    sms_sender=None,
    research_mode=False,
    organisation='organisation-id',
    branding='govuk'
):
    return {
        'id': id_,
        'name': name,
        'users': users,
        'message_limit': message_limit,
        'active': active,
        'restricted': restricted,
        'email_from': email_from,
        'reply_to_email_address': reply_to_email_address,
        'sms_sender': sms_sender,
        'research_mode': research_mode,
        'organisation': organisation,
        'branding': branding,
        'created_at': str(datetime.utcnow())
    }


def template_json(service_id,
                  id_,
                  name="sample template",
                  type_="sms",
                  content="template content",
                  subject=None,
                  version=1,
                  archived=False):
    template = {
        'id': id_,
        'name': name,
        'template_type': type_,
        'content': content,
        'service': service_id,
        'version': version,
        'updated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
        'archived': archived
    }
    if subject is not None:
        template['subject'] = subject
    return template


def template_version_json(service_id,
                          id_,
                          created_by,
                          version=1,
                          created_at=None,
                          **kwargs):
    template = template_json(service_id, id_, **kwargs)
    template['created_by'] = created_by_json(
        created_by.id,
        created_by.name,
        created_by.email_address
    )
    if created_at is None:
        created_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
    template['created_at'] = created_at
    template['version'] = version
    return template


def api_key_json(id_, name, expiry_date=None):
    return {'id': id_,
            'name': name,
            'expiry_date': expiry_date
            }


def invite_json(id_, from_user, service_id, email_address, permissions, created_at, status):
    return {'id': id_,
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


def job_json(
    service_id,
    created_by,
    job_id=None,
    template_id=None,
    template_version=1,
    created_at=None,
    bucket_name='',
    original_file_name="thisisatest.csv",
    notification_count=1,
    notifications_sent=1,
    notifications_requested=1,
    job_status='Delivered',
    scheduled_for=''
):
    if job_id is None:
        job_id = str(generate_uuid())
    if template_id is None:
        template_id = str(generate_uuid())
    if created_at is None:
        created_at = str(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f%z'))
    data = {
        'id': job_id,
        'service': service_id,
        'template': template_id,
        'template_version': template_version,
        'original_file_name': original_file_name,
        'created_at': created_at,
        'notification_count': notification_count,
        'notifications_sent': notifications_sent,
        'notifications_requested': notifications_requested,
        'job_status': job_status,
        'statistics': [],
        'created_by': created_by_json(
            created_by.id,
            created_by.name,
            created_by.email_address
        ),
        'scheduled_for': scheduled_for
    }
    return data


def notification_json(
    service_id,
    job=None,
    template=None,
    to='07123456789',
    status=None,
    sent_at=None,
    job_row_number=None,
    created_at=None,
    updated_at=None,
    with_links=False,
    rows=5
):
    if template is None:
        template = template_json(service_id, str(generate_uuid()))
    if sent_at is None:
        sent_at = str(datetime.utcnow().time())
    if created_at is None:
        created_at = datetime.now(timezone.utc).isoformat()
    if updated_at is None:
        updated_at = str((datetime.utcnow() + timedelta(minutes=1)).time())
    if status is None:
        status = 'delivered'
    links = {}
    if with_links:
        links = {
            'prev': '/service/{}/notifications'.format(service_id),
            'next': '/service/{}/notifications'.format(service_id),
            'last': '/service/{}/notifications'.format(service_id)
        }
    job_payload = None
    if job:
        job_payload = {'id': job['id'], 'original_file_name': job['original_file_name']}

    data = {
        'notifications': [{
            'id': uuid.uuid4(),
            'to': to,
            'template': {
                'id': template['id'],
                'name': template['name'],
                'template_type': template['template_type']},
            'job': job_payload,
            'sent_at': sent_at,
            'status': status,
            'created_at': created_at,
            'updated_at': updated_at,
            'job_row_number': job_row_number,
            'template_version': template['version']
        } for i in range(rows)],
        'total': rows,
        'page_size': 50,
        'links': links
    }
    return data


def single_notification_json(
    service_id,
    job=None,
    template=None,
    status=None,
    sent_at=None,
    created_at=None,
    updated_at=None
):
    if template is None:
        template = template_json(service_id, str(generate_uuid()))
    if sent_at is None:
        sent_at = str(datetime.utcnow())
    if created_at is None:
        created_at = str(datetime.utcnow())
    if updated_at is None:
        updated_at = str(datetime.utcnow() + timedelta(minutes=1))
    if status is None:
        status = 'delivered'
    job_payload = None
    if job:
        job_payload = {'id': job['id'], 'original_file_name': job['original_file_name']}

    data = {
        'sent_at': sent_at,
        'billable_units': 1,
        'status': status,
        'created_at': created_at,
        'reference': None,
        'updated_at': updated_at,
        'template_version': 5,
        'service': service_id,
        'id': '29441662-17ce-4ffe-9502-fcaed73b2826',
        'template': template,
        'job_row_number': 0,
        'notification_type': 'sms',
        'api_key': None,
        'job': job_payload,
        'sent_by': 'mmg'
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
    mocker.patch('app.service_api_client.update_service', return_value=service)
    mocker.patch('app.service_api_client.update_service_with_properties', return_value=service)
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
                print(resp.status_code)
                pytest.fail("Invalid permissions set for endpoint {}".format(route))
    return resp
