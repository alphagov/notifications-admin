from datetime import date
from unittest.mock import patch

import pytest
import werkzeug

from app.models.service import Service
from app.notify_client import NotifyAdminAPIClient
from app.notify_client.notification_api_client import notification_api_client
from tests import service_json
from tests.conftest import (
    create_api_user_active,
    create_platform_admin_user,
    set_config,
)


@pytest.mark.parametrize('method', [
    'put',
    'post',
    'delete'
])
@pytest.mark.parametrize('user', [
    create_api_user_active(),
    create_platform_admin_user(),
], ids=['api_user', 'platform_admin'])
@pytest.mark.parametrize('service', [
    service_json(active=True),
    None
], ids=['active_service', 'no_service'])
def test_active_service_can_be_modified(notify_admin, method, user, service):
    api_client = NotifyAdminAPIClient()

    with notify_admin.test_request_context() as request_context, notify_admin.test_client() as client:
        client.login(user)
        request_context.service = Service(service)

        with patch.object(api_client, 'request') as request:
            ret = getattr(api_client, method)('url', 'data')

    assert request.called
    assert ret == request.return_value


@pytest.mark.parametrize('method', [
    'put',
    'post',
    'delete'
])
def test_inactive_service_cannot_be_modified_by_normal_user(notify_admin, api_user_active, method):
    api_client = NotifyAdminAPIClient()

    with notify_admin.test_request_context() as request_context, notify_admin.test_client() as client:
        client.login(api_user_active)
        request_context.service = Service(service_json(active=False))

        with patch.object(api_client, 'request') as request:
            with pytest.raises(werkzeug.exceptions.Forbidden):
                getattr(api_client, method)('url', 'data')

    assert not request.called


@pytest.mark.parametrize('method', [
    'put',
    'post',
    'delete'
])
def test_inactive_service_can_be_modified_by_platform_admin(notify_admin, platform_admin_user, method):
    api_client = NotifyAdminAPIClient()

    with notify_admin.test_request_context() as request_context, notify_admin.test_client() as client:
        client.login(platform_admin_user)
        request_context.service = Service(service_json(active=False))

        with patch.object(api_client, 'request') as request:
            ret = getattr(api_client, method)('url', 'data')

    assert request.called
    assert ret == request.return_value


def test_generate_headers_sets_standard_headers(notify_admin):
    api_client = NotifyAdminAPIClient()
    with set_config(notify_admin, 'ROUTE_SECRET_KEY_1', 'proxy-secret'):
        api_client.init_app(notify_admin)

    # with patch('app.notify_client.has_request_context', return_value=False):
    headers = api_client.generate_headers('api_token')

    assert set(headers.keys()) == {'Authorization', 'Content-type', 'User-agent', 'X-Custom-Forwarder'}
    assert headers['Authorization'] == 'Bearer api_token'
    assert headers['Content-type'] == 'application/json'
    assert headers['User-agent'].startswith('NOTIFY-API-PYTHON-CLIENT')
    assert headers['X-Custom-Forwarder'] == 'proxy-secret'


def test_generate_headers_sets_request_id_if_in_request_context(notify_admin):
    api_client = NotifyAdminAPIClient()
    api_client.init_app(notify_admin)

    with notify_admin.test_request_context() as request_context:
        headers = api_client.generate_headers('api_token')

    assert set(headers.keys()) == {
        'Authorization', 'Content-type', 'User-agent', 'X-Custom-Forwarder', 'X-B3-TraceId', 'X-B3-SpanId',
    }
    assert headers['X-B3-TraceId'] == request_context.request.request_id
    assert headers['X-B3-SpanId'] == request_context.request.span_id


def test_get_notification_status_by_service(mocker):
    mock_get = mocker.patch.object(notification_api_client, 'get')
    start_date = date(2019, 4, 1)
    end_date = date(2019, 4, 30)

    notification_api_client.get_notification_status_by_service(start_date, end_date)

    mock_get.assert_called_once_with(
        url='service/monthly-data-by-service',
        params={'start_date': '2019-04-01', 'end_date': '2019-04-30'}
    )
