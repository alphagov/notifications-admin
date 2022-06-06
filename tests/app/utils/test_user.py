import pytest
from flask import request
from werkzeug.exceptions import Forbidden

from app.main.views.index import index
from app.utils.user import user_has_permissions
from tests.conftest import create_user, sample_uuid

_user_with_permissions = create_user(
    id=sample_uuid(),
    permissions={'foo': ['manage_users', 'manage_templates', 'manage_settings']},
    services=['foo', 'bar'],
)


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
):
    request.view_args.update({'service_id': 'foo'})
    client_request.login(_user_with_permissions)

    decorator = user_has_permissions(*permissions)
    decorated_index = decorator(index)
    decorated_index()


def test_restrict_admin_usage(
    client_request,
    platform_admin_user,
):
    request.view_args.update({'service_id': 'foo'})
    client_request.login(platform_admin_user)

    decorator = user_has_permissions(restrict_admin_usage=True)
    decorated_index = decorator(index)

    with pytest.raises(Forbidden):
        decorated_index()


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
    user = create_user(
        id=sample_uuid(),
        organisations=['org_1', 'org_2'],
    )
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
    user = create_user(
        id=sample_uuid(),
        organisations=['org_1', 'org_2'],
    )
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
    client_request.login(_user_with_permissions)
    request.view_args = {'service_id': 'bar'}

    @user_has_permissions()
    def index():
        pass

    index()
