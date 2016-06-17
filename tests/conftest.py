import uuid
from datetime import date, datetime, timedelta
from unittest.mock import Mock
import pytest

from app import create_app

from . import (
    service_json,
    TestClient,
    template_json,
    template_version_json,
    api_key_json,
    job_json,
    notification_json,
    invite_json,
    sample_uuid,
    generate_uuid)
from app.notify_client.models import (
    User,
    InvitedUser
)

from notifications_python_client.errors import HTTPError


@pytest.fixture(scope='session')
def app_(request):
    app = create_app()

    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    app.test_client_class = TestClient
    return app


@pytest.fixture(scope='function')
def service_one(api_user_active):
    return service_json(SERVICE_ONE_ID, 'service one', [api_user_active.id])


@pytest.fixture(scope='function')
def mock_send_sms(request, mocker):
    return mocker.patch("app.service_api_client.send_sms")


@pytest.fixture(scope='function')
def fake_uuid():
    return sample_uuid()


@pytest.fixture(scope='function')
def mock_get_service(mocker, api_user_active):
    def _get(service_id):
        service = service_json(
            service_id, "Test Service", [api_user_active.id], message_limit=1000,
            active=False, restricted=True)
        return {'data': service}

    return mocker.patch('app.service_api_client.get_service', side_effect=_get)


@pytest.fixture(scope='function')
def mock_get_live_service(mocker, api_user_active):
    def _get(service_id):
        service = service_json(
            service_id,
            "Test Service",
            [api_user_active.id],
            message_limit=1000,
            active=False,
            restricted=False)
        return {'data': service}

    return mocker.patch('app.service_api_client.get_service', side_effect=_get)


@pytest.fixture(scope='function')
def mock_create_service(mocker):
    def _create(service_name, active, message_limit, restricted, user_id, email_from):
        service = service_json(
            101, service_name, [user_id], message_limit=message_limit,
            active=active, restricted=restricted, email_from=email_from)
        return service['id']

    return mocker.patch(
        'app.service_api_client.create_service', side_effect=_create)


@pytest.fixture(scope='function')
def mock_update_service(mocker):
    def _update(service_id,
                service_name,
                active,
                message_limit,
                restricted,
                users,
                email_from,
                reply_to_email_address=None):
        service = service_json(
            service_id, service_name, users, message_limit=message_limit,
            active=active, restricted=restricted, email_from=email_from, reply_to_email_address=reply_to_email_address)
        return {'data': service}

    return mocker.patch(
        'app.service_api_client.update_service', side_effect=_update, autospec=True)


@pytest.fixture(scope='function')
def mock_update_service_raise_httperror_duplicate_name(mocker):
    def _update(service_id,
                service_name,
                active,
                limit,
                restricted,
                users,
                email_from):
        json_mock = Mock(return_value={'message': {'name': ["Duplicate service name '{}'".format(service_name)]}})
        resp_mock = Mock(status_code=400, json=json_mock)
        http_error = HTTPError(response=resp_mock, message="Default message")
        raise http_error

    return mocker.patch(
        'app.service_api_client.update_service', side_effect=_update)


SERVICE_ONE_ID = "596364a0-858e-42c8-9062-a8fe822260eb"
SERVICE_TWO_ID = "147ad62a-2951-4fa1-9ca0-093cd1a52c52"


@pytest.fixture(scope='function')
def mock_get_services(mocker, fake_uuid, user=None):
    if user is None:
        user = active_user_with_permissions(fake_uuid)

    def _create(user_id=None):
        service_one = service_json(
            SERVICE_ONE_ID, "service_one", [user.id], 1000, True, False)
        service_two = service_json(
            SERVICE_TWO_ID, "service_two", [user.id], 1000, True, False)
        return {'data': [service_one, service_two]}

    return mocker.patch(
        'app.service_api_client.get_services', side_effect=_create)


@pytest.fixture(scope='function')
def mock_get_services_with_no_services(mocker, fake_uuid, user=None):
    if user is None:
        user = active_user_with_permissions(fake_uuid)

    def _create(user_id=None):
        return {'data': []}

    return mocker.patch(
        'app.service_api_client.get_services', side_effect=_create)


@pytest.fixture(scope='function')
def mock_get_services_with_one_service(mocker, fake_uuid, user=None):
    if user is None:
        user = api_user_active(fake_uuid)

    def _create(user_id=None):
        return {'data': [service_json(
            SERVICE_ONE_ID, "service_one", [user.id], 1000, True, False
        )]}

    return mocker.patch(
        'app.service_api_client.get_services', side_effect=_create)


@pytest.fixture(scope='function')
def mock_delete_service(mocker, mock_get_service):
    def _delete(service_id):
        return mock_get_service.side_effect(service_id)

    return mocker.patch(
        'app.service_api_client.delete_service', side_effect=_delete)


@pytest.fixture(scope='function')
def mock_get_service_statistics(mocker):
    def _create(service_id, limit_days=None):
        return {'data': [{}]}

    return mocker.patch(
        'app.statistics_api_client.get_statistics_for_service', side_effect=_create)


@pytest.fixture(scope='function')
def mock_get_service_statistics_for_day(mocker):

    stats = {'day': datetime.today().date().strftime('%Y-%m-%d'),
             'emails_delivered': 0,
             'sms_requested': 0,
             'sms_delivered': 0,
             'sms_failed': 0,
             'emails_requested': 0,
             'emails_failed': 0,
             'service': fake_uuid,
             'id': fake_uuid}

    def _stats(service_id, day):
        return {'data': stats}

    return mocker.patch(
        'app.statistics_api_client.get_statistics_for_service_for_day', side_effect=_stats)


@pytest.fixture(scope='function')
def mock_get_aggregate_service_statistics(mocker):
    def _create(service_id, limit_days=None):
        return {'data': [{}]}

    return mocker.patch(
        'app.statistics_api_client.get_7_day_aggregate_for_service', side_effect=_create)


@pytest.fixture(scope='function')
def mock_get_all_service_statistics(mocker):
    def _create(day):
        return {'data': []}

    return mocker.patch(
        'app.statistics_api_client.get_statistics_for_all_services_for_day', side_effect=_create)


@pytest.fixture(scope='function')
def mock_get_service_template(mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id, template_id, "Two week reminder", "sms", "Your vehicle tax is about to expire")
        if version:
            template.update({'version': version})
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.get_service_template',
        side_effect=_get
    )


@pytest.fixture(scope='function')
def mock_get_template_version(mocker, fake_uuid, user=None):
    if user is None:
        user = api_user_active(fake_uuid)

    def _get(service_id, template_id, version):
        template_version = template_version_json(
            service_id,
            template_id,
            user,
            version=version
        )
        return {'data': template_version}

    return mocker.patch(
        'app.service_api_client.get_service_template',
        side_effect=_get
    )


@pytest.fixture(scope='function')
def mock_get_template_versions(mocker, fake_uuid, user=None):
    if user is None:
        user = api_user_active(fake_uuid)

    def _get(service_id, template_id):
        template_version = template_version_json(
            service_id,
            template_id,
            user,
            version=1
        )
        return {'data': [template_version]}

    return mocker.patch(
        'app.service_api_client.get_service_template_versions',
        side_effect=_get
    )


@pytest.fixture(scope='function')
def mock_get_service_template_with_placeholders(mocker):
    def _get(service_id, template_id):
        template = template_json(
            service_id, template_id, "Two week reminder", "sms", "((name)), your vehicle tax is about to expire"
        )
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.get_service_template',
        side_effect=_get
    )


@pytest.fixture(scope='function')
def mock_get_service_email_template(mocker):
    def _create(service_id, template_id):
        template = template_json(
            service_id,
            template_id,
            "Two week reminder",
            "email",
            "Your vehicle tax is about to expire", "Subject")
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.get_service_template', side_effect=_create)


@pytest.fixture(scope='function')
def mock_create_service_template(mocker, fake_uuid):
    def _create(name, type_, content, service, subject=None):
        template = template_json(
            fake_uuid, name, type_, content, service)
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.create_service_template',
        side_effect=_create)


@pytest.fixture(scope='function')
def mock_update_service_template(mocker):
    def _update(id_, name, type_, content, service, subject=None):
        template = template_json(
            service, id_, name, type_, content, subject)
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.update_service_template',
        side_effect=_update)


@pytest.fixture(scope='function')
def mock_create_service_template_content_too_big(mocker):
    def _create(name, type_, content, service, subject=None):
        json_mock = Mock(return_value={
            'message': {'content': ["Content has a character count greater than the limit of 459"]},
            'result': 'error'
        })
        resp_mock = Mock(status_code=400, json=json_mock)
        http_error = HTTPError(
            response=resp_mock,
            message={'content': ["Content has a character count greater than the limit of 459"]})
        raise http_error

    return mocker.patch(
        'app.service_api_client.create_service_template',
        side_effect=_create)


@pytest.fixture(scope='function')
def mock_update_service_template_400_content_too_big(mocker):
    def _update(id_, name, type_, content, service, subject=None):
        json_mock = Mock(return_value={
            'message': {'content': ["Content has a character count greater than the limit of 459"]},
            'result': 'error'
        })
        resp_mock = Mock(status_code=400, json=json_mock)
        http_error = HTTPError(
            response=resp_mock,
            message={'content': ["Content has a character count greater than the limit of 459"]})
        raise http_error

    return mocker.patch(
        'app.service_api_client.update_service_template',
        side_effect=_update)


@pytest.fixture(scope='function')
def mock_get_service_templates(mocker):
    uuid1 = str(generate_uuid())
    uuid2 = str(generate_uuid())
    uuid3 = str(generate_uuid())
    uuid4 = str(generate_uuid())

    def _create(service_id):
        return {'data': [
            template_json(
                service_id, uuid1, "sms_template_one", "sms", "sms template one content"
            ),
            template_json(
                service_id, uuid2, "sms_template_two", "sms", "sms template two content"
            ),
            template_json(
                service_id, uuid3, "email_template_one", "email", "email template one content"
            ),
            template_json(
                service_id, uuid4, "email_template_two", "email", "email template two content"
            )
        ]}

    return mocker.patch(
        'app.service_api_client.get_service_templates',
        side_effect=_create)


@pytest.fixture(scope='function')
def mock_delete_service_template(mocker):
    def _delete(service_id, template_id):
        template = template_json(
            service_id, template_id, "Template to delete", "sms", "content to be deleted")
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.delete_service_template', side_effect=_delete)


@pytest.fixture(scope='function')
def api_user_pending(fake_uuid):
    from app.notify_client.user_api_client import User
    user_data = {'id': fake_uuid,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '07700 900762',
                 'state': 'pending',
                 'failed_login_count': 0,
                 'permissions': {}
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def platform_admin_user(fake_uuid):
    from app.notify_client.user_api_client import User
    user_data = {'id': fake_uuid,
                 'name': 'Platform admin user',
                 'password': 'somepassword',
                 'email_address': 'platform@admin.gov.uk',
                 'mobile_number': '07700 900762',
                 'state': 'active',
                 'failed_login_count': 0,
                 'permissions': {},
                 'platform_admin': True
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def api_user_active(fake_uuid):
    from app.notify_client.user_api_client import User
    user_data = {'id': fake_uuid,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '07700 900762',
                 'state': 'active',
                 'failed_login_count': 0,
                 'permissions': {},
                 'platform_admin': False
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def active_user_with_permissions(fake_uuid):
    from app.notify_client.user_api_client import User

    user_data = {'id': fake_uuid,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '07700 900762',
                 'state': 'active',
                 'failed_login_count': 0,
                 'permissions': {SERVICE_ONE_ID: ['send_texts',
                                                  'send_emails',
                                                  'send_letters',
                                                  'manage_users',
                                                  'manage_templates',
                                                  'manage_settings',
                                                  'manage_api_keys',
                                                  'view_activity']},
                 'platform_admin': False
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def api_user_locked(fake_uuid):
    from app.notify_client.user_api_client import User
    user_data = {'id': fake_uuid,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '07700 900762',
                 'state': 'active',
                 'failed_login_count': 5,
                 'permissions': {}
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def api_user_request_password_reset(fake_uuid):
    from app.notify_client.user_api_client import User
    user_data = {'id': fake_uuid,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '07700 900762',
                 'state': 'active',
                 'failed_login_count': 5,
                 'permissions': {},
                 'password_changed_at': None
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def api_user_changed_password(fake_uuid):
    from app.notify_client.user_api_client import User
    user_data = {'id': fake_uuid,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '07700 900762',
                 'state': 'active',
                 'failed_login_count': 5,
                 'permissions': {},
                 'password_changed_at': str(datetime.utcnow() + timedelta(minutes=1))
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def mock_register_user(mocker, api_user_pending):
    def _register(name, email_address, mobile_number, password):
        api_user_pending.name = name
        api_user_pending.email_address = email_address
        api_user_pending.mobile_number = mobile_number
        api_user_pending.password = password
        return api_user_pending

    return mocker.patch('app.user_api_client.register_user', side_effect=_register)


@pytest.fixture(scope='function')
def mock_get_user(mocker, user=None):
    if user is None:
        user = api_user_active(fake_uuid())

    def _get_user(id_):
        user.id = id_
        return user

    return mocker.patch(
        'app.user_api_client.get_user', side_effect=_get_user)


@pytest.fixture(scope='function')
def mock_get_locked_user(mocker, api_user_locked):
    return mock_get_user(mocker, user=api_user_locked)


@pytest.fixture(scope='function')
def mock_get_user_locked(mocker, api_user_locked):
    return mocker.patch(
        'app.user_api_client.get_user', return_value=api_user_locked)


@pytest.fixture(scope='function')
def mock_get_user_pending(mocker, api_user_pending):
    return mocker.patch(
        'app.user_api_client.get_user', return_value=api_user_pending)


@pytest.fixture(scope='function')
def mock_get_user_by_email(mocker, user=None):
    if user is None:
        user = api_user_active(fake_uuid())

    def _get_user(email_address):
        user._email_address = email_address
        return user

    return mocker.patch('app.user_api_client.get_user_by_email', side_effect=_get_user)


@pytest.fixture(scope='function')
def mock_get_locked_user_by_email(mocker, api_user_locked):
    return mock_get_user_by_email(mocker, user=api_user_locked)


@pytest.fixture(scope='function')
def mock_get_user_with_permissions(mocker, api_user_active):
    def _get_user(id):
        api_user_active._permissions[''] = ['manage_users', 'manage_templates', 'manage_settings']
        return api_user_active

    return mocker.patch(
        'app.user_api_client.get_user', side_effect=_get_user)


@pytest.fixture(scope='function')
def mock_dont_get_user_by_email(mocker):
    def _get_user(email_address):
        return None

    return mocker.patch(
        'app.user_api_client.get_user_by_email',
        side_effect=_get_user,
        autospec=True
    )


@pytest.fixture(scope='function')
def mock_get_user_by_email_request_password_reset(mocker, api_user_request_password_reset):
    return mocker.patch(
        'app.user_api_client.get_user_by_email',
        return_value=api_user_request_password_reset)


@pytest.fixture(scope='function')
def mock_get_user_by_email_user_changed_password(mocker, api_user_changed_password):
    return mocker.patch(
        'app.user_api_client.get_user_by_email',
        return_value=api_user_changed_password)


@pytest.fixture(scope='function')
def mock_get_user_by_email_locked(mocker, api_user_locked):
    return mocker.patch(
        'app.user_api_client.get_user_by_email', return_value=api_user_locked)


@pytest.fixture(scope='function')
def mock_get_user_by_email_inactive(mocker, api_user_pending):
    return mocker.patch('app.user_api_client.get_user_by_email', return_value=api_user_pending)


@pytest.fixture(scope='function')
def mock_get_user_by_email_pending(mocker, api_user_pending):
    return mocker.patch(
        'app.user_api_client.get_user_by_email',
        return_value=api_user_pending)


@pytest.fixture(scope='function')
def mock_get_user_by_email_not_found(mocker, api_user_active):
    def _get_user(email):
        json_mock = Mock(return_value={'message': "Not found", 'result': 'error'})
        resp_mock = Mock(status_code=404, json=json_mock)
        http_error = HTTPError(response=resp_mock, message="Default message")
        raise http_error

    return mocker.patch(
        'app.user_api_client.get_user_by_email',
        side_effect=_get_user)


@pytest.fixture(scope='function')
def mock_verify_password(mocker):
    def _verify_password(user, password):
        return True

    return mocker.patch(
        'app.user_api_client.verify_password',
        side_effect=_verify_password)


@pytest.fixture(scope='function')
def mock_update_user(mocker):
    def _update(user):
        return user

    return mocker.patch('app.user_api_client.update_user', side_effect=_update)


@pytest.fixture(scope='function')
def mock_is_email_unique(mocker):
    return mocker.patch('app.user_api_client.is_email_unique', return_value=True)


@pytest.fixture(scope='function')
def mock_is_email_not_unique(mocker):
    return mocker.patch('app.user_api_client.is_email_unique', return_value=False)


@pytest.fixture(scope='function')
def mock_get_all_users_from_api(mocker):
    return mocker.patch('app.user_api_client.get_users', return_value={'data': []})


@pytest.fixture(scope='function')
def mock_create_api_key(mocker):
    def _create(service_id, key_name):
        import uuid
        return {'data': str(generate_uuid())}

    return mocker.patch('app.api_key_api_client.create_api_key', side_effect=_create)


@pytest.fixture(scope='function')
def mock_revoke_api_key(mocker):
    def _revoke(service_id, key_id):
        return {}

    return mocker.patch(
        'app.api_key_api_client.revoke_api_key',
        side_effect=_revoke)


@pytest.fixture(scope='function')
def mock_get_api_keys(mocker):
    def _get_keys(service_id, key_id=None):
        keys = {'apiKeys': [api_key_json(service_id, 'some key name'),
                            api_key_json(service_id, 'another key name', expiry_date=str(date.fromtimestamp(0)))]}
        return keys

    return mocker.patch('app.api_key_api_client.get_api_keys', side_effect=_get_keys)


@pytest.fixture(scope='function')
def mock_get_no_api_keys(mocker):
    def _get_keys(service_id):
        keys = {'apiKeys': []}
        return keys

    return mocker.patch('app.api_key_api_client.get_api_keys', side_effect=_get_keys)


@pytest.fixture(scope='function')
def mock_login(mocker, mock_get_user, mock_update_user, mock_events):
    def _verify_code(user_id, code, code_type):
        return True, ''

    def _no_services(user_id=None):
        return {'data': []}

    return (
        mocker.patch(
            'app.user_api_client.check_verify_code',
            side_effect=_verify_code
        ),
        mocker.patch(
            'app.service_api_client.get_services',
            side_effect=_no_services
        )
    )


@pytest.fixture(scope='function')
def mock_send_verify_code(mocker):
    return mocker.patch('app.user_api_client.send_verify_code')


@pytest.fixture(scope='function')
def mock_send_verify_email(mocker):
    return mocker.patch('app.user_api_client.send_verify_email')


@pytest.fixture(scope='function')
def mock_check_verify_code(mocker):
    def _verify(user_id, code, code_type):
        return True, ''

    return mocker.patch(
        'app.user_api_client.check_verify_code',
        side_effect=_verify)


@pytest.fixture(scope='function')
def mock_check_verify_code_code_not_found(mocker):
    def _verify(user_id, code, code_type):
        return False, 'Code not found'

    return mocker.patch(
        'app.user_api_client.check_verify_code',
        side_effect=_verify)


@pytest.fixture(scope='function')
def mock_check_verify_code_code_expired(mocker):
    def _verify(user_id, code, code_type):
        return False, 'Code has expired'

    return mocker.patch(
        'app.user_api_client.check_verify_code',
        side_effect=_verify)


@pytest.fixture(scope='function')
def mock_create_job(mocker, api_user_active):
    def _create(job_id, service_id, template_id, file_name, notification_count):
        job_data = job_json(
            service_id,
            api_user_active,
            job_id=job_id,
            template_id=template_id,
            bucket_name='service-{}-notify'.format(job_id),
            original_file_name='{}.csv'.format(job_id),
            notification_count=notification_count)
        return job_data

    return mocker.patch('app.job_api_client.create_job', side_effect=_create)


@pytest.fixture(scope='function')
def mock_get_job(mocker, api_user_active):
    def _get_job(service_id, job_id):
        job_data = job_json(service_id, api_user_active, job_id=job_id)
        return {"data": job_data}

    return mocker.patch('app.job_api_client.get_job', side_effect=_get_job)


@pytest.fixture(scope='function')
def mock_get_jobs(mocker, api_user_active):
    def _get_jobs(service_id, limit_days=None):
        data = []
        for i in range(5):
            job_data = job_json(service_id, api_user_active)
            data.append(job_data)
        return {"data": data}

    return mocker.patch('app.job_api_client.get_job', side_effect=_get_jobs)


@pytest.fixture(scope='function')
def mock_get_notifications(mocker, api_user_active):
    def _get_notifications(service_id,
                           job_id=None,
                           page=1,
                           page_size=50,
                           template_type=None,
                           status=None,
                           limit_days=None):
        job = None
        if job_id is not None:
            job = job_json(service_id, api_user_active, job_id=job_id)
        return notification_json(service_id, job=job)

    return mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=_get_notifications
    )


@pytest.fixture(scope='function')
def mock_get_notifications_with_previous_next(mocker):
    def _get_notifications(service_id,
                           job_id=None,
                           page=1,
                           template_type=None,
                           status=None,
                           limit_days=None):
        return notification_json(service_id, with_links=True)

    return mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=_get_notifications
    )


@pytest.fixture(scope='function')
def mock_has_permissions(mocker):
    def _has_permission(permissions=None, any_=False, admin_override=False):
        return True

    return mocker.patch(
        'app.notify_client.user_api_client.User.has_permissions',
        side_effect=_has_permission)


@pytest.fixture(scope='function')
def mock_get_users_by_service(mocker):
    def _get_users_for_service(service_id):
        data = [{'id': 1,
                 'logged_in_at': None,
                 'mobile_number': '+447700900986',
                 'permissions': {SERVICE_ONE_ID: ['send_texts',
                                                  'send_emails',
                                                  'send_letters',
                                                  'manage_users',
                                                  'manage_templates',
                                                  'manage_settings',
                                                  'manage_api_keys',
                                                  'access_developer_docs']},
                 'state': 'active',
                 'password_changed_at': None,
                 'name': 'Test User',
                 'email_address': 'notify@digital.cabinet-office.gov.uk',
                 'failed_login_count': 0}]
        return [User(data[0])]

    return mocker.patch('app.user_api_client.get_users_for_service', side_effect=_get_users_for_service, autospec=True)


@pytest.fixture(scope='function')
def mock_s3_upload(mocker):
    def _upload(service_id, filedata, region):
        return fake_uuid()

    return mocker.patch('app.main.views.send.s3upload', side_effect=_upload)


@pytest.fixture(scope='function')
def mock_s3_download(mocker, content=None):
    if not content:
        content = """
            phone number,name
            +447700900986,John
            +447700900986,Smith
        """

    def _download(service_id, upload_id):
        return content
    return mocker.patch('app.main.views.send.s3download', side_effect=_download)


@pytest.fixture(scope='function')
def sample_invite(mocker, service_one, status='pending'):
    id_ = str(generate_uuid())
    from_user = service_one['users'][0]
    email_address = 'invited_user@test.gov.uk'
    service_id = service_one['id']
    permissions = 'send_messages,manage_service,manage_api_keys'
    created_at = str(datetime.utcnow())
    return invite_json(id_, from_user, service_id, email_address, permissions, created_at, status)


@pytest.fixture(scope='function')
def sample_invited_user(mocker, sample_invite):
    return InvitedUser(**sample_invite)


@pytest.fixture(scope='function')
def mock_create_invite(mocker, sample_invite):
    def _create_invite(from_user, service_id, email_address, permissions):
        sample_invite['from_user'] = from_user
        sample_invite['service'] = service_id
        sample_invite['email_address'] = email_address
        sample_invite['status'] = 'pending'
        sample_invite['permissions'] = permissions
        return InvitedUser(**sample_invite)

    return mocker.patch('app.invite_api_client.create_invite', side_effect=_create_invite)


@pytest.fixture(scope='function')
def mock_get_invites_for_service(mocker, service_one, sample_invite):
    import copy

    def _get_invites(service_id):
        data = []
        for i in range(0, 5):
            invite = copy.copy(sample_invite)
            invite['email_address'] = 'user_{}@testnotify.gov.uk'.format(i)
            data.append(InvitedUser(**invite))
        return data

    return mocker.patch('app.invite_api_client.get_invites_for_service', side_effect=_get_invites)


@pytest.fixture(scope='function')
def mock_check_invite_token(mocker, sample_invite):
    def _check_token(token):
        return InvitedUser(**sample_invite)

    return mocker.patch('app.invite_api_client.check_token', side_effect=_check_token)


@pytest.fixture(scope='function')
def mock_accept_invite(mocker, sample_invite):
    def _accept(service_id, invite_id):
        return InvitedUser(**sample_invite)

    return mocker.patch('app.invite_api_client.accept_invite', side_effect=_accept)


@pytest.fixture(scope='function')
def mock_add_user_to_service(mocker, service_one, api_user_active):
    def _add_user(service_id, user_id, permissions):
        return api_user_active

    return mocker.patch('app.user_api_client.add_user_to_service', side_effect=_add_user)


@pytest.fixture(scope='function')
def mock_set_user_permissions(mocker):
    return mocker.patch('app.user_api_client.set_user_permissions', return_value=None)


@pytest.fixture(scope='function')
def mock_remove_user_from_service(mocker):
    return mocker.patch('app.service_api_client.remove_user_from_service', return_value=None)


@pytest.fixture(scope='function')
def mock_get_template_statistics(mocker, service_one, fake_uuid):
    template = template_json(service_one['id'], fake_uuid, "Test template", "sms", "Something very interesting")
    data = {
        "usage_count": 1,
        "template": {
            "name": template['name'],
            "template_type": template['template_type'],
            "id": template['id']
        },
        "service": template['service'],
        "id": str(generate_uuid()),
        "day": "2016-04-04",
        "updated_at": "2016-04-04T12:00:00.000000+00:00"
    }

    def _get_stats(service_id, limit_days=None):
        return [data]

    return mocker.patch(
        'app.template_statistics_client.get_template_statistics_for_service', side_effect=_get_stats)


@pytest.fixture(scope='function')
def mock_get_template_statistics_for_template(mocker, service_one):
    def _get_stats(service_id, template_id):
        template = template_json(service_id, template_id, "Test template", "sms", "Something very interesting")
        return [
            {
                "usage_count": 1,
                "template": {
                    "name": template['name'],
                    "template_type": template['template_type'],
                    "id": template['id']
                },
                "service": template['service'],
                "id": str(generate_uuid()),
                "day": "2016-04-04",
                "updated_at": "2016-04-04T12:00:00.000000+00:00"
            }
        ]

    return mocker.patch(
        'app.template_statistics_client.get_template_statistics_for_template', side_effect=_get_stats)


@pytest.fixture(scope='function')
def mock_get_usage(mocker, service_one, fake_uuid):
    def _get_usage(service_id):
        return {'data': {
            "sms_count": 123,
            "email_count": 456
        }}

    return mocker.patch(
        'app.service_api_client.get_service_usage', side_effect=_get_usage)


@pytest.fixture(scope='function')
def mock_events(mocker):
    def _create_event(event_type, event_data):
        return {'some': 'data'}

    return mocker.patch('app.events_api_client.create_event', side_effect=_create_event)
