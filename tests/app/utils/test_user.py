import pytest
from flask import request
from werkzeug.exceptions import Forbidden

from app.main.views.index import index
from app.utils.user import user_has_permissions


def _test_permissions(
    client_request,
    usr,
    permissions,
    kwargs=None,
):
    request.view_args.update({'service_id': 'foo'})
    client_request.login(usr)

    decorator = user_has_permissions(*permissions, **(kwargs or {}))
    decorated_index = decorator(index)
    return decorated_index()


def test_user_has_permissions_on_endpoint_fail(
    client_request,
    mock_get_service,
):
    with pytest.raises(Forbidden):
        _test_permissions(
            client_request,
            _user_with_permissions(),
            ['send_messages'],
        )


def test_user_has_permissions_success(
    client_request,
    mocker,
):
    _test_permissions(
        client_request,
        _user_with_permissions(),
        ['manage_service'],
    )


def test_user_has_permissions_or(
    client_request,
):
    _test_permissions(
        client_request,
        _user_with_permissions(),
        ['send_messages', 'manage_service'],
    )


def test_user_has_permissions_multiple(
    client_request,
):
    _test_permissions(
        client_request,
        _user_with_permissions(),
        ['manage_templates', 'manage_service'],
    )


def test_exact_permissions(
    client_request,
):
    _test_permissions(
        client_request,
        _user_with_permissions(),
        ['manage_service', 'manage_templates'],
    )


def test_platform_admin_user_can_access_page_that_has_no_permissions(
    client_request,
    platform_admin_user,
):
    _test_permissions(
        client_request,
        platform_admin_user,
        [],
    )


def test_platform_admin_user_can_not_access_page(
    client_request,
    platform_admin_user,
    mock_get_service,
):
    with pytest.raises(Forbidden):
        _test_permissions(
            client_request,
            platform_admin_user,
            [],
            kwargs={'restrict_admin_usage': True},
        )


def test_no_user_returns_redirect_to_sign_in(
    client_request
):
    client_request.logout()
    decorator = user_has_permissions()
    decorated_index = decorator(index)
    response = decorated_index()
    assert response.status_code == 302
    assert response.location.startswith('/sign-in?next=')


def test_user_has_permissions_for_organisation(
    client_request,
):
    user = _user_with_permissions()
    user['organisations'] = ['org_1', 'org_2']
    client_request.login(user)

    request.view_args = {'org_id': 'org_2'}

    @user_has_permissions()
    def index():
        pass

    index()


def test_platform_admin_can_see_orgs_they_dont_have(
    client_request,
    platform_admin_user,
):
    platform_admin_user['organisations'] = []
    client_request.login(platform_admin_user)

    request.view_args = {'org_id': 'org_2'}

    @user_has_permissions()
    def index():
        pass

    index()


def test_cant_use_decorator_without_view_args(
    client_request,
    platform_admin_user,
):
    client_request.login(platform_admin_user)

    request.view_args = {}

    @user_has_permissions()
    def index():
        pass

    with pytest.raises(NotImplementedError):
        index()


def test_user_doesnt_have_permissions_for_organisation(
    client_request,
):
    user = _user_with_permissions()
    user['organisations'] = ['org_1', 'org_2']
    client_request.login(user)

    request.view_args = {'org_id': 'org_3'}

    @user_has_permissions()
    def index():
        pass

    with pytest.raises(Forbidden):
        index()


def test_user_with_no_permissions_to_service_goes_to_templates(
    client_request,
):
    user = _user_with_permissions()
    client_request.login(user)
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
