import pytest
from flask import request
from werkzeug.exceptions import Forbidden

from app.utils.user import user_has_permissions


@pytest.mark.parametrize('permissions', (
    pytest.param(
        ['send_messages'],
        marks=pytest.mark.xfail(raises=Forbidden),
    ),
    ['manage_service'],
    ['send_messages', 'manage_service'],
    ['manage_templates', 'manage_service'],
    ['manage_service', 'manage_templates'],
    [],
))
def test_permissions(
    client_request,
    permissions,
    api_user_active,
):
    request.view_args.update({'service_id': 'foo'})

    api_user_active['permissions'] = {'foo': ['manage_users', 'manage_templates', 'manage_settings']}
    api_user_active['services'] = ['foo', 'bar']

    client_request.login(api_user_active)

    @user_has_permissions(*permissions)
    def index():
        pass

    index()


def test_restrict_admin_usage(
    client_request,
    platform_admin_user,
):
    request.view_args.update({'service_id': 'foo'})
    client_request.login(platform_admin_user)

    @user_has_permissions(restrict_admin_usage=True)
    def index():
        pass

    with pytest.raises(Forbidden):
        index()


def test_no_user_returns_redirect_to_sign_in(
    client_request
):
    client_request.logout()

    @user_has_permissions()
    def index():
        pass

    response = index()
    assert response.status_code == 302
    assert response.location.startswith('/sign-in?next=')


def test_user_has_permissions_for_organisation(
    client_request,
    api_user_active,
):
    api_user_active['organisations'] = ['org_1', 'org_2']
    client_request.login(api_user_active)

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
    api_user_active,
):
    api_user_active['organisations'] = ['org_1', 'org_2']
    client_request.login(api_user_active)

    request.view_args = {'org_id': 'org_3'}

    @user_has_permissions()
    def index():
        pass

    with pytest.raises(Forbidden):
        index()


def test_user_with_no_permissions_to_service_goes_to_templates(
    client_request,
    api_user_active,
):
    api_user_active['permissions'] = {'foo': ['manage_users', 'manage_templates', 'manage_settings']}
    api_user_active['services'] = ['foo', 'bar']
    client_request.login(api_user_active)
    request.view_args = {'service_id': 'bar'}

    @user_has_permissions()
    def index():
        pass

    index()
