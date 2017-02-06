import pytest
from app.utils import user_has_permissions
from app.main.views.index import index
from werkzeug.exceptions import Forbidden, Unauthorized
from flask import request


def _test_permissions(
    client,
    usr,
    permissions,
    service_id,
    will_succeed,
    any_=False,
    admin_override=False,
):
    request.view_args.update({'service_id': service_id})
    if usr:
        client.login(usr)
    decorator = user_has_permissions(*permissions, any_=any_, admin_override=admin_override)
    decorated_index = decorator(index)
    if will_succeed:
        response = decorated_index()
    else:
        try:
            response = decorated_index()
            pytest.fail("Failed to throw a forbidden or unauthorised exception")
        except (Forbidden, Unauthorized):
            pass


def test_user_has_permissions_on_endpoint_fail(
    client,
    mocker,
):
    user = _user_with_permissions()
    mocker.patch('app.user_api_client.get_user', return_value=user)
    _test_permissions(
        client,
        user,
        ['something'],
        '',
        False)


def test_user_has_permissions_success(
    client,
    mocker,
):
    user = _user_with_permissions()
    mocker.patch('app.user_api_client.get_user', return_value=user)
    _test_permissions(
        client,
        user,
        ['manage_users'],
        '',
        True)


def test_user_has_permissions_or(
    client,
    mocker,
):
    user = _user_with_permissions()
    mocker.patch('app.user_api_client.get_user', return_value=user)
    _test_permissions(
        client,
        user,
        ['something', 'manage_users'],
        '',
        True,
        any_=True)


def test_user_has_permissions_multiple(
    client,
    mocker,
):
    user = _user_with_permissions()
    mocker.patch('app.user_api_client.get_user', return_value=user)
    _test_permissions(
        client,
        user,
        ['manage_templates', 'manage_users'],
        '',
        will_succeed=True)


def test_exact_permissions(
    client,
    mocker,
):
    user = _user_with_permissions()
    mocker.patch('app.user_api_client.get_user', return_value=user)
    _test_permissions(
        client,
        user,
        ['manage_users', 'manage_templates', 'manage_settings'],
        '',
        True)


def test_platform_admin_user_can_access_page(
    client,
    platform_admin_user,
    mocker,
):
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    _test_permissions(
        client,
        platform_admin_user,
        [],
        '',
        will_succeed=True,
        admin_override=True)


def test_platform_admin_user_can_not_access_page(
    client,
    platform_admin_user,
    mocker,
):
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    _test_permissions(
        client,
        platform_admin_user,
        [],
        '',
        will_succeed=False,
        admin_override=False)


def test_no_user_returns_401_unauth(
    client
):
    from flask_login import current_user
    assert not current_user.is_authenticated
    _test_permissions(
        client,
        None,
        [],
        '',
        will_succeed=False)


def _user_with_permissions():
    from app.notify_client.user_api_client import User

    user_data = {'id': 999,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '+4412341234',
                 'state': 'active',
                 'failed_login_count': 0,
                 'permissions': {'': ['manage_users', 'manage_templates', 'manage_settings']},
                 'platform_admin': False
                 }
    user = User(user_data)
    return user
