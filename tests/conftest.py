import os
from datetime import date

import pytest
from alembic.command import upgrade
from alembic.config import Config
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager
from sqlalchemy.schema import MetaData

from app import create_app
from . import (
    create_test_user, service_json, TestClient,
    get_test_user, template_json, api_key_json)


@pytest.fixture(scope='session')
def app_(request):
    app = create_app('test')

    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    app.test_client_class = TestClient
    return app


@pytest.fixture(scope='function')
def service_one(request, api_user_active):
    return service_json(1, 'service one', [api_user_active.id])


# @pytest.fixture(scope='function')
# def active_user(request, db_, db_session):
#     usr = get_test_user()
#     if usr:
#         return usr
#     return create_test_user('active')


@pytest.fixture(scope='function')
def mock_send_sms(request, mocker):
    return mocker.patch("app.notifications_api_client.send_sms")


@pytest.fixture(scope='function')
def mock_send_email(request, mocker):
    return mocker.patch("app.notifications_api_client.send_email")


@pytest.fixture(scope='function')
def mock_get_service(mocker, api_user_active):
    def _create(service_id):
        service = service_json(
            service_id, "Test Service", [api_user_active.id], limit=1000,
            active=False, restricted=True)
        return {'data': service, 'token': 1}

    return mocker.patch('app.notifications_api_client.get_service', side_effect=_create)


@pytest.fixture(scope='function')
def mock_create_service(mocker):
    def _create(service_name, active, limit, restricted, user_id):
        service = service_json(
            101, service_name, [user_id], limit=limit,
            active=active, restricted=restricted)
        return {'data': service}

    mock_class = mocker.patch(
        'app.notifications_api_client.create_service', side_effect=_create)
    return mock_class


@pytest.fixture(scope='function')
def mock_update_service(mocker):
    def _update(service_id,
                service_name,
                active,
                limit,
                restricted,
                users):
        service = service_json(
            service_id, service_name, users, limit=limit,
            active=active, restricted=restricted)
        return {'data': service}

    mock_class = mocker.patch(
        'app.notifications_api_client.update_service', side_effect=_update)
    return mock_class


@pytest.fixture(scope='function')
def mock_get_services(mocker, api_user_active):
    def _create():
        service_one = service_json(
            1, "service_one", [api_user_active.id], 1000, True, False)
        service_two = service_json(
            2, "service_two", [api_user_active.id], 1000, True, False)
        return {'data': [service_one, service_two]}

    mock_class = mocker.patch(
        'app.notifications_api_client.get_services', side_effect=_create)
    return mock_class


@pytest.fixture(scope='function')
def mock_delete_service(mocker, mock_get_service):
    def _delete(service_id):
        return mock_get_service.side_effect(service_id)

    mock_class = mocker.patch(
        'app.notifications_api_client.delete_service', side_effect=_delete)
    return mock_class


@pytest.fixture(scope='function')
def mock_get_service_template(mocker):
    def _create(service_id, template_id):
        template = template_json(
            template_id, "Template Name", "sms", "template content", service_id)
        return {'data': template}

    return mocker.patch(
        'app.notifications_api_client.get_service_template',
        side_effect=_create)


@pytest.fixture(scope='function')
def mock_create_service_template(mocker):
    def _create(name, type_, content, service):
        template = template_json(
            101, name, type_, content, service)
        return {'data': template}

    mock_class = mocker.patch(
        'app.notifications_api_client.create_service_template',
        side_effect=_create)
    return mock_class


@pytest.fixture(scope='function')
def mock_update_service_template(mocker):
    def _update(id_, name, type_, content, service):
        template = template_json(
            id_, name, type_, content, service)
        return {'data': template}

    mock_class = mocker.patch(
        'app.notifications_api_client.update_service_template',
        side_effect=_update)
    return mock_class


@pytest.fixture(scope='function')
def mock_get_service_templates(mocker):
    def _create(service_id):
        template_one = template_json(
            1, "template_one", "sms", "template one content", service_id)
        template_two = template_json(
            2, "template_two", "sms", "template two content", service_id)
        return {'data': [template_one, template_two]}

    mock_class = mocker.patch(
        'app.notifications_api_client.get_service_templates',
        side_effect=_create)
    return mock_class


@pytest.fixture(scope='function')
def mock_delete_service_template(mocker):
    def _delete(service_id, template_id):
        template = template_json(
            template_id, "Template to delete",
            "sms", "content to be deleted", service_id)
        return {'data': template}

    return mocker.patch(
        'app.notifications_api_client.delete_service_template', side_effect=_delete)


@pytest.fixture(scope='function')
def api_user_pending(mocker):
    from app.notify_client.user_api_client import User
    user_data = {'id': 1,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '+4412341234',
                 'state': 'pending',
                 'failed_login_count': 0
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def api_user_active(mocker):
    from app.notify_client.user_api_client import User
    user_data = {'id': 1,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '+4412341234',
                 'state': 'active',
                 'failed_login_count': 0
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def mock_register_user(mocker, api_user_pending):
    def _register(name, email_address, mobile_number, password):
        api_user_pending.fields['name'] = name
        api_user_pending.fields['email_address'] = email_address
        api_user_pending.fields['mobile_number'] = mobile_number
        api_user_pending.fields['password'] = password
        return api_user_pending
    return mocker.patch('app.user_api_client.register_user', side_effect=_register)


@pytest.fixture(scope='function')
def mock_user_loader(mocker, api_user_active):
    mock_class = mocker.patch('app.main.dao.users_dao.get_user_by_id')
    mock_class.return_value = api_user_active
    return mock_class


@pytest.fixture(scope='function')
def mock_activate_user(mocker, api_user_pending):
    def _activate(api_user_pending):
        api_user_pending.state = 'active'
        return api_user_pending
    return mocker.patch('app.user_api_client.update_user', side_effect=_activate)


@pytest.fixture(scope='function')
def mock_user_dao_get_user(mocker, api_user_active):
    def _get_user(id):
        return api_user_active
    return mocker.patch('app.main.dao.users_dao.get_user_by_id', side_effect=_get_user)


@pytest.fixture(scope='function')
def mock_get_user(mocker, api_user_active):
    def _get_user(id):
        return api_user_active
    return mocker.patch(
        'app.user_api_client.get_user', side_effect=_get_user)


@pytest.fixture(scope='function')
def mock_user_dao_get_by_email(mocker, api_user_active):

    def _get_user(email_address):
        api_user_active.fields['email_address'] = email_address
        return api_user_active
    return mocker.patch('app.main.dao.users_dao.get_user_by_email', side_effect=_get_user)


@pytest.fixture(scope='function')
def mock_inactive_user_dao_get_by_email(mocker, api_user_pending):
    def _get_user(email_address):
        api_user_pending.fields['email_address'] = email_address
        api_user_pending.fields['is_locked'] = True
        return api_user_pending
    return mocker.patch('app.main.dao.users_dao.get_user_by_email', side_effect=_get_user)


@pytest.fixture(scope='function')
def mock_user_by_email_not_found(mocker):
    return mocker.patch('app.main.dao.users_dao.get_user_by_email', return_value=None)


@pytest.fixture(scope='function')
def mock_get_user_by_email(mocker, api_user_active):

    def _get_user(email_address):
        api_user_active.fields['email_address'] = email_address
        return api_user_active
    return mocker.patch(
        'app.user_api_client.get_user_by_email', side_effect=_get_user)


@pytest.fixture(scope='function')
def mock_get_user_by_email_not_found(mocker):
    return mocker.patch(
        'app.user_api_client.get_user_by_email', return_value=None)


@pytest.fixture(scope='function')
def mock_user_dao_checkpassword(mocker, api_user_active):

    def _check(api_user_active, password):
        return True
    return mocker.patch('app.main.dao.users_dao.verify_password', side_effect=_check)


@pytest.fixture(scope='function')
def mock_verify_password(mocker):
    def _verify_password(user, password):
        return True
    return mocker.patch(
        'app.user_api_client.verify_password',
        side_effect=_verify_password)


@pytest.fixture(scope='function')
def mock_user_dao_update_email(mocker, api_user_active):

    def _update(id, email_address):
        api_user_active.fields['email_address'] = email_address
        return api_user_active
    return mocker.patch('app.main.dao.users_dao.update_email_address', side_effect=_update)


@pytest.fixture(scope='function')
def mock_user_dao_update_mobile(mocker, api_user_active):

    def _update(id, mobile_number):
        api_user_active.fields['mobile_number'] = mobile_number
        return api_user_active
    return mocker.patch('app.main.dao.users_dao.update_mobile_number', side_effect=_update)


@pytest.fixture(scope='function')
def mock_user_dao_password_reset(mocker, api_user_active):

    def _reset(email):
        api_user_active.state = 'request_password_reset'
    return mocker.patch('app.main.dao.users_dao.request_password_reset', side_effect=_reset)


@pytest.fixture(scope='function')
def mock_update_user(mocker):

    def _update(user):
        return user
    return mocker.patch('app.user_api_client.update_user', side_effect=_update)


@pytest.fixture(scope='function')
def mock_user_dao_get_new_password(mocker, api_user_active):
    api_user_active.state = 'request_password_reset'
    mock_class = mocker.patch('app.main.dao.users_dao.get_user_by_email')
    mock_class.return_value = api_user_active
    return mock_class


@pytest.fixture(scope='function')
def mock_create_api_key(mocker):
    def _create(service_id, key_name):
        import uuid
        return {'data': str(uuid.uuid4())}

    mock_class = mocker.patch('app.api_key_api_client.create_api_key', side_effect=_create)
    return mock_class


@pytest.fixture(scope='function')
def mock_revoke_api_key(mocker):
    def _revoke(service_id, key_id):
        return {}

    mock_class = mocker.patch(
        'app.api_key_api_client.revoke_api_key',
        side_effect=_revoke)
    return mock_class


@pytest.fixture(scope='function')
def mock_get_api_keys(mocker):
    def _get_keys(service_id, key_id=None):
        keys = {'apiKeys': [api_key_json(1, 'some key name'),
                            api_key_json(2, 'another key name', expiry_date=str(date.fromtimestamp(0)))]}
        return keys

    mock_class = mocker.patch('app.api_key_api_client.get_api_keys', side_effect=_get_keys)
    return mock_class


@pytest.fixture(scope='function')
def mock_get_no_api_keys(mocker):
    def _get_keys(service_id):
        keys = {'apiKeys': []}
        return keys

    mock_class = mocker.patch('app.api_key_api_client.get_api_keys', side_effect=_get_keys)
    return mock_class


@pytest.fixture(scope='function')
def mock_login(mocker, mock_user_dao_get_user, mock_update_user):
    def _verify_code(user_id, code, code_type):
        return True, ''
    mock_class = mocker.patch(
        'app.user_api_client.check_verify_code',
        side_effect=_verify_code)
    return mock_class


@pytest.fixture(scope='function')
def mock_send_verify_code(mocker):
    mock_class = mocker.patch('app.user_api_client.send_verify_code')
    return mock_class


@pytest.fixture(scope='function')
def mock_check_verify_code(mocker):
    def _verify(user_id, code, code_type):
        return True, ''
    mock_class = mocker.patch(
        'app.user_api_client.check_verify_code',
        side_effect=_verify)
    return mock_class


@pytest.fixture(scope='function')
def mock_check_verify_code_code_not_found(mocker):
    def _verify(user_id, code, code_type):
        return False, 'Code not found'
    mock_class = mocker.patch(
        'app.user_api_client.check_verify_code',
        side_effect=_verify)
    return mock_class


@pytest.fixture(scope='function')
def mock_check_verify_code_code_expired(mocker):
    def _verify(user_id, code, code_type):
        return False, 'Code has expired'
    mock_class = mocker.patch(
        'app.user_api_client.check_verify_code',
        side_effect=_verify)
    return mock_class
