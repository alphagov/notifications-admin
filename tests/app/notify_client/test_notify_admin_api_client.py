import uuid
import pytest
from unittest.mock import patch

import werkzeug

from tests import service_json
from tests.conftest import api_user_active, platform_admin_user
from app.notify_client import NotifyAdminAPIClient


@pytest.mark.parametrize('method', [
    'put',
    'post',
    'delete'
])
@pytest.mark.parametrize('user', [
    api_user_active(str(uuid.uuid4())),
    platform_admin_user(str(uuid.uuid4()))
], ids=['api_user', 'platform_admin'])
@pytest.mark.parametrize('service', [
    service_json(active=True),
    None
], ids=['active_service', 'no_service'])
def test_active_service_can_be_modified(app_, method, user, service):
    api_client = NotifyAdminAPIClient('api_key', 'base_url', 'service_id')

    with app_.test_request_context() as request_context, app_.test_client() as client:
        client.login(user)
        request_context.service = service

        with patch.object(api_client, 'request') as request:
            ret = getattr(api_client, method)('url', 'data')

    assert request.called
    assert ret == request.return_value


@pytest.mark.parametrize('method', [
    'put',
    'post',
    'delete'
])
def test_inactive_service_cannot_be_modified_by_normal_user(app_, api_user_active, method):
    api_client = NotifyAdminAPIClient('api_key', 'base_url', 'service_id')

    with app_.test_request_context() as request_context, app_.test_client() as client:
        client.login(api_user_active)
        request_context.service = service_json(active=False)

        with patch.object(api_client, 'request') as request:
            with pytest.raises(werkzeug.exceptions.Forbidden):
                getattr(api_client, method)('url', 'data')

    assert not request.called


@pytest.mark.parametrize('method', [
    'put',
    'post',
    'delete'
])
def test_inactive_service_can_be_modified_by_platform_admin(app_, platform_admin_user, method):
    api_client = NotifyAdminAPIClient('api_key', 'base_url', 'service_id')

    with app_.test_request_context() as request_context, app_.test_client() as client:
        client.login(platform_admin_user)
        request_context.service = service_json(active=False)

        with patch.object(api_client, 'request') as request:
            ret = getattr(api_client, method)('url', 'data')

    assert request.called
    assert ret == request.return_value
