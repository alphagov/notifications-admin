import pytest
from flask import request
from werkzeug.exceptions import Forbidden, Unauthorized

from app.main.views.index import index
from app.utils.user import user_has_permissions


def _test_permissions(
    client,
    usr,
    permissions,
    will_succeed,
    kwargs=None,
):
    request.view_args.update({'service_id': 'foo'})
    if usr:
        client.login(usr)

    decorator = user_has_permissions(*permissions, **(kwargs or {}))
    decorated_index = decorator(index)

    if will_succeed:
        decorated_index()
    else:
        try:
            if (
                decorated_index().location != '/sign-in?next=%2F' or
                decorated_index().status_code != 302
            ):
                pytest.fail("Failed to throw a forbidden or unauthorised exception")
        except (Forbidden, Unauthorized):
            pass


def test_user_has_permissions_on_endpoint_fail(
    client,
    mocker,
    mock_get_service,
):
    user = _user_with_permissions()
    mocker.patch('app.user_api_client.get_user', return_value=user)
    _test_permissions(
        client,
        user,
        ['send_messages'],
        will_succeed=False)


def test_user_has_permissions_success(
    client,
    mocker,
):
    user = _user_with_permissions()
    mocker.patch('app.user_api_client.get_user', return_value=user)
    _test_permissions(
        client,
        user,
        ['manage_service'],
        will_succeed=True)


def test_user_has_permissions_or(
    client,
    mocker,
):
    user = _user_with_permissions()
    mocker.patch('app.user_api_client.get_user', return_value=user)
    _test_permissions(
        client,
        user,
        ['send_messages', 'manage_service'],
        will_succeed=True)


def test_user_has_permissions_multiple(
    client,
    mocker,
):
    user = _user_with_permissions()
    mocker.patch('app.user_api_client.get_user', return_value=user)
    _test_permissions(
        client,
        user,
        ['manage_templates', 'manage_service'],
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
        ['manage_service', 'manage_templates'],
        will_succeed=True)


def test_platform_admin_user_can_access_page_that_has_no_permissions(
    client,
    platform_admin_user,
    mocker,
):
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    _test_permissions(
        client,
        platform_admin_user,
        [],
        will_succeed=True)


def test_platform_admin_user_can_not_access_page(
    client,
    platform_admin_user,
    mocker,
    mock_get_service,
):
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    _test_permissions(
        client,
        platform_admin_user,
        [],
        will_succeed=False,
        kwargs={'restrict_admin_usage': True})


def test_no_user_returns_401_unauth(
    client
):
    from flask_login import current_user
    assert not current_user.is_authenticated
    _test_permissions(
        client,
        None,
        [],
        will_succeed=False)


def test_user_has_permissions_for_organisation(
    client,
    mocker,
):
    user = _user_with_permissions()
    user['organisations'] = ['org_1', 'org_2']
    mocker.patch('app.user_api_client.get_user', return_value=user)
    client.login(user)

    request.view_args = {'org_id': 'org_2'}

    @user_has_permissions()
    def index():
        pass

    index()


def test_platform_admin_can_see_orgs_they_dont_have(
    client,
    platform_admin_user,
    mocker,
):
    platform_admin_user['organisations'] = []
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    client.login(platform_admin_user)

    request.view_args = {'org_id': 'org_2'}

    @user_has_permissions()
    def index():
        pass

    index()


def test_cant_use_decorator_without_view_args(
    client,
    platform_admin_user,
    mocker,
):
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    client.login(platform_admin_user)

    request.view_args = {}

    @user_has_permissions()
    def index():
        pass

    with pytest.raises(NotImplementedError):
        index()


def test_user_doesnt_have_permissions_for_organisation(
    client,
    mocker,
):
    user = _user_with_permissions()
    user['organisations'] = ['org_1', 'org_2']
    mocker.patch('app.user_api_client.get_user', return_value=user)
    client.login(user)

    request.view_args = {'org_id': 'org_3'}

    @user_has_permissions()
    def index():
        pass

    with pytest.raises(Forbidden):
        index()


def test_user_with_no_permissions_to_service_goes_to_templates(
        client,
        mocker
):
    user = _user_with_permissions()
    mocker.patch('app.user_api_client.get_user', return_value=user)
    client.login(user)
    request.view_args = {'service_id': 'bar'}

    @user_has_permissions()
    def index():
        pass

    index()


def _user_with_permissions():
    user_data = {'id': 999,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '+4412341234',
                 'state': 'active',
                 'failed_login_count': 0,
                 'permissions': {'foo': ['manage_users', 'manage_templates', 'manage_settings']},
                 'platform_admin': False,
                 'organisations': ['org_1', 'org_2'],
                 'services': ['foo', 'bar'],
                 'current_session_id': None,
                 }
    return user_data
