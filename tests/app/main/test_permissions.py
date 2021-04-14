import ast
import inspect
import re

import pytest
from flask import current_app, request
from werkzeug.exceptions import Forbidden, Unauthorized

from app.main.views.index import index
from app.models.roles_and_permissions import (
    translate_permissions_from_admin_roles_to_db,
    translate_permissions_from_db_to_admin_roles,
)
from app.utils import user_has_permissions
from tests import service_json
from tests.conftest import (
    ORGANISATION_ID,
    ORGANISATION_TWO_ID,
    SERVICE_ONE_ID,
    SERVICE_TWO_ID,
)


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


def test_translate_permissions_from_db_to_admin_roles():
    db_perms = ['send_texts', 'send_emails', 'send_letters', 'manage_templates', 'some_unknown_permission']
    roles = translate_permissions_from_db_to_admin_roles(db_perms)
    assert roles == {'send_messages', 'manage_templates', 'some_unknown_permission'}


def test_translate_permissions_from_admin_roles_to_db():
    roles = ['send_messages', 'manage_templates', 'some_unknown_permission']
    db_perms = translate_permissions_from_admin_roles_to_db(roles)
    assert db_perms == {'send_texts', 'send_emails', 'send_letters', 'manage_templates', 'some_unknown_permission'}


@pytest.mark.parametrize(
    'user_services, user_organisations, expected_status, organisation_checked',
    (
        ([SERVICE_ONE_ID], [], 200, False),
        ([SERVICE_ONE_ID, SERVICE_TWO_ID], [], 200, False),
        ([], [ORGANISATION_ID], 200, True),
        ([SERVICE_ONE_ID], [ORGANISATION_ID], 200, False),
        ([], [], 403, True),
        ([SERVICE_TWO_ID], [], 403, True),
        ([SERVICE_TWO_ID], [ORGANISATION_ID], 200, True),
        ([SERVICE_ONE_ID, SERVICE_TWO_ID], [ORGANISATION_ID], 200, False),
        ([], [ORGANISATION_TWO_ID], 403, True),
        ([], [ORGANISATION_ID, ORGANISATION_TWO_ID], 200, True),
    )
)
def test_services_pages_that_org_users_are_allowed_to_see(
    client_request,
    mocker,
    api_user_active,
    mock_get_usage,
    mock_get_billable_units,
    mock_get_free_sms_fragment_limit,
    mock_get_service,
    mock_get_invites_for_service,
    mock_get_users_by_service,
    mock_get_template_folders,
    mock_get_organisation,
    mock_has_jobs,
    user_services,
    user_organisations,
    expected_status,
    organisation_checked,
):
    api_user_active['services'] = user_services
    api_user_active['organisations'] = user_organisations
    api_user_active['permissions'] = {
        service_id: ['manage_service']
        for service_id in user_services
    }
    service = service_json(
        name='SERVICE WITH ORG',
        id_=SERVICE_ONE_ID,
        users=[api_user_active['id']],
        organisation_id=ORGANISATION_ID,
    )

    mock_get_service = mocker.patch(
        'app.notify_client.service_api_client.service_api_client.get_service',
        return_value={'data': service}
    )
    client_request.login(
        api_user_active,
        service=service if SERVICE_ONE_ID in user_services else None,
    )

    endpoints = (
        'main.usage',
        'main.manage_users',
    )

    for endpoint in endpoints:
        client_request.get(
            endpoint,
            service_id=SERVICE_ONE_ID,
            _expected_status=expected_status,
        )

    assert mock_get_service.called is organisation_checked


def test_service_navigation_for_org_user(
    client_request,
    mocker,
    api_user_active,
    mock_get_usage,
    mock_get_billable_units,
    mock_get_free_sms_fragment_limit,
    mock_get_service,
    mock_get_invites_for_service,
    mock_get_users_by_service,
    mock_get_organisation,
):
    api_user_active['services'] = []
    api_user_active['organisations'] = [ORGANISATION_ID]
    service = service_json(
        id_=SERVICE_ONE_ID,
        organisation_id=ORGANISATION_ID,
    )
    mocker.patch(
        'app.service_api_client.get_service',
        return_value={'data': service}
    )
    client_request.login(api_user_active, service=service)

    page = client_request.get(
        'main.usage',
        service_id=SERVICE_ONE_ID,
    )
    assert [
        item.text.strip() for item in page.select('nav.navigation a')
    ] == [
        'Usage',
        'Team members',
    ]


@pytest.mark.parametrize('user_organisations, expected_menu_items, expected_status', [
    (
        [],
        (
            'Templates',
            'Sent messages',
            'Uploads',
            'Team members',
        ),
        403,
    ),
    (
        [ORGANISATION_ID],
        (
            'Templates',
            'Sent messages',
            'Uploads',
            'Team members',
            'Usage',
        ),
        200,
    ),
])
def test_service_user_without_manage_service_permission_can_see_usage_page_when_org_user(
    client_request,
    mocker,
    active_caseworking_user,
    mock_has_no_jobs,
    mock_get_usage,
    mock_get_billable_units,
    mock_get_free_sms_fragment_limit,
    mock_get_service,
    mock_get_invites_for_service,
    mock_get_users_by_service,
    mock_get_organisation,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_api_keys,
    user_organisations,
    expected_status,
    expected_menu_items,
):
    active_caseworking_user['services'] = [SERVICE_ONE_ID]
    active_caseworking_user['organisations'] = user_organisations
    service = service_json(
        id_=SERVICE_ONE_ID,
        organisation_id=ORGANISATION_ID,
    )
    mocker.patch(
        'app.service_api_client.get_service',
        return_value={'data': service}
    )
    client_request.login(active_caseworking_user, service=service)
    page = client_request.get(
        'main.choose_template',
        service_id=SERVICE_ONE_ID,
    )
    assert tuple(
        item.text.strip() for item in page.select('nav.navigation a')
    ) == expected_menu_items

    client_request.get(
        'main.usage',
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_status,
    )


def get_name_of_decorator_from_ast_node(node):
    if isinstance(node, ast.Name):
        return str(node.id)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return get_name_of_decorator_from_ast_node(node.func)
    if isinstance(node, ast.Attribute):
        return node.value.id
    return '{}.{}'.format(node.func.value.id, node.func.attr)


def get_decorators_for_function(function):
    for node in ast.walk(ast.parse(inspect.getsource(function))):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                yield get_name_of_decorator_from_ast_node(decorator)


SERVICE_ID_ARGUMENT = 'service_id'
ORGANISATION_ID_ARGUMENT = 'org_id'


def get_routes_and_decorators(argument_name=None):
    import app.main.views as views
    for module_name, module in inspect.getmembers(views):
        for function_name, function in inspect.getmembers(module):
            if inspect.isfunction(function):
                decorators = list(get_decorators_for_function(function))
                if 'main.route' in decorators and (
                    not argument_name or
                    argument_name in inspect.signature(function).parameters.keys()
                ):
                    yield '{}.{}'.format(module_name, function_name), decorators


def format_decorators(decorators, indent=8):
    return '\n'.join(
        '{}@{}'.format(' ' * indent, decorator)
        for decorator in decorators
    )


def test_code_to_extract_decorators_works_with_known_examples():
    assert (
        'templates.choose_template',
        ['main.route', 'main.route', 'main.route', 'main.route', 'main.route', 'main.route', 'user_has_permissions'],
    ) in list(
        get_routes_and_decorators(SERVICE_ID_ARGUMENT)
    )
    assert (
        'organisations.organisation_dashboard',
        ['main.route', 'user_has_permissions'],
    ) in list(
        get_routes_and_decorators(ORGANISATION_ID_ARGUMENT)
    )
    assert (
        'platform_admin.platform_admin',
        ['main.route', 'user_is_platform_admin'],
    ) in list(
        get_routes_and_decorators()
    )


def test_routes_have_permissions_decorators():

    for endpoint, decorators in (
        list(get_routes_and_decorators(SERVICE_ID_ARGUMENT)) +
        list(get_routes_and_decorators(ORGANISATION_ID_ARGUMENT))
    ):
        file, function = endpoint.split('.')

        assert 'user_is_logged_in' not in decorators, (
            '@user_is_logged_in used on service or organisation specific endpoint\n'
            'Use @user_has_permissions() or @user_is_platform_admin only\n'
            'app/main/views/{}.py::{}\n'
        ).format(file, function)

        if 'user_is_platform_admin' in decorators:
            continue

        assert 'user_has_permissions' in decorators, (
            'Missing @user_has_permissions decorator\n'
            'Use @user_has_permissions() or @user_is_platform_admin instead\n'
            'app/main/views/{}.py::{}\n'
        ).format(file, function)

    for _endpoint, decorators in get_routes_and_decorators():

        assert 'login_required' not in decorators, (
            '@login_required found\n'
            'For consistency, use @user_is_logged_in() instead (from app.utils)\n'
            'app/main/views/{}.py::{}\n'
        ).format(file, function)

        if 'user_is_platform_admin' in decorators:
            assert 'user_has_permissions' not in decorators, (
                '@user_has_permissions and @user_is_platform_admin decorating same function\n'
                'You can only use one of these at a time\n'
                'app/main/views/{}.py::{}\n'
            ).format(file, function)
            assert 'user_is_logged_in' not in decorators, (
                '@user_is_logged_in used with @user_is_platform_admin\n'
                'Use @user_is_platform_admin only\n'
                'app/main/views/{}.py::{}\n'
            ).format(file, function)


def test_routes_require_uuids(client_request):
    for rule in current_app.url_map.iter_rules():
        for param in re.findall('<([^>]*)>', rule.rule):
            if '_id' in param and not param.startswith('uuid:'):
                pytest.fail((
                    'Should be <uuid:{}> in {}'
                ).format(param, rule.rule))
