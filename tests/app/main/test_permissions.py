import ast
import inspect
import re

import pytest
from flask import current_app

from tests import sample_uuid, service_json
from tests.conftest import (
    ORGANISATION_ID,
    ORGANISATION_TWO_ID,
    SERVICE_ONE_ID,
    SERVICE_TWO_ID,
    create_folder,
)


@pytest.mark.parametrize(
    "user_services, user_organisations, expected_status, organisation_checked",
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
    ),
)
@pytest.mark.parametrize(
    "endpoint, extra_args",
    (
        ("main.usage", {}),
        ("main.manage_users", {}),
        ("main.choose_template", {"template_id": sample_uuid()}),
        ("main.choose_template", {"template_folder_id": sample_uuid()}),
        ("main.view_template", {"template_id": sample_uuid()}),
        ("main.view_template_versions", {"template_id": sample_uuid()}),
        ("main.view_template_version", {"template_id": sample_uuid(), "version": 1}),
        ("no_cookie.view_letter_template_preview", {"template_id": sample_uuid(), "filetype": "pdf"}),
    ),
)
def test_services_pages_that_org_users_are_allowed_to_see(
    client_request,
    mocker,
    api_user_active,
    mock_get_annual_usage_for_service,
    mock_get_monthly_usage_for_service,
    mock_get_free_sms_fragment_limit,
    mocked_get_service_data,
    mock_get_invites_for_service,
    mock_get_users_by_service,
    mock_get_organisation,
    mock_has_jobs,
    mock_get_service_templates,
    mock_get_service_template,
    mock_get_template_versions,
    mock_get_template_version,
    mock_get_api_keys,
    mock_template_preview,
    user_services,
    user_organisations,
    expected_status,
    organisation_checked,
    endpoint,
    extra_args,
):
    api_user_active["services"] = user_services
    api_user_active["organisations"] = user_organisations
    api_user_active["permissions"] = {service_id: ["manage_users", "manage_settings"] for service_id in user_services}
    service = service_json(
        name="SERVICE WITH ORG",
        id_=SERVICE_ONE_ID,
        users=[api_user_active["id"]],
        organisation_id=ORGANISATION_ID,
    )

    mocked_get_service_data[service["id"]] = service
    mocker.patch("app.template_folder_api_client.get_template_folders", return_value=[create_folder(id=sample_uuid())])

    client_request.login(
        api_user_active,
        service=service if SERVICE_ONE_ID in user_services else None,
    )

    client_request.get(
        endpoint, service_id=SERVICE_ONE_ID, _expected_status=expected_status, _test_page_title=False, **extra_args
    )


# check both regular users and org users
@pytest.mark.parametrize("user_organisations", [[], [ORGANISATION_ID]])
def test_users_cannot_see_inactive_service(client_request, api_user_active, user_organisations):
    service = service_json(
        name="SERVICE WITH ORG",
        id_=SERVICE_ONE_ID,
        users=[api_user_active["id"]],
        organisation_id=ORGANISATION_ID,
        active=False,
    )
    # the API removes inactive services from user["services"] and removes all permissions too, so even if the user
    # is a member of the service their user json will return empty
    api_user_active["services"] = []
    api_user_active["permissions"] = {SERVICE_ONE_ID: []}
    api_user_active["organisations"] = user_organisations
    client_request.login(api_user_active, service=service)

    client_request.get("main.choose_template", service_id=SERVICE_ONE_ID, _expected_status=403)


def test_platform_admin_can_still_update_inactive_service(
    client_request,
    api_user_active,
    mock_update_service,
):
    service = service_json(
        name="SERVICE WITH ORG",
        id_=SERVICE_ONE_ID,
        users=[api_user_active["id"]],
        organisation_id=ORGANISATION_ID,
        active=False,
    )
    api_user_active["services"] = []
    api_user_active["permissions"] = {}
    api_user_active["organisations"] = []
    api_user_active["platform_admin"] = True
    client_request.login(api_user_active, service=service)

    client_request.post(
        "main.service_name_change", service_id=SERVICE_ONE_ID, _data={"name": "New Name"}, _expected_status=302
    )

    assert mock_update_service.called


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_service_navigation_for_org_user(
    client_request,
    mocker,
    api_user_active,
    mock_get_annual_usage_for_service,
    mock_get_monthly_usage_for_service,
    mock_get_free_sms_fragment_limit,
    mock_get_service,
    mock_get_invites_for_service,
    mock_get_users_by_service,
    mock_get_organisation,
):
    api_user_active["services"] = []
    api_user_active["organisations"] = [ORGANISATION_ID]
    service = service_json(
        id_=SERVICE_ONE_ID,
        organisation_id=ORGANISATION_ID,
    )
    mocker.patch("app.service_api_client.get_service", return_value={"data": service})
    client_request.login(api_user_active, service=service)

    page = client_request.get(
        "main.usage",
        service_id=SERVICE_ONE_ID,
    )
    assert [item.text.strip() for item in page.select("nav.navigation a")] == [
        "Usage",
        "Templates",
        "Team members",
    ]


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "user_organisations, expected_menu_items, expected_status",
    [
        (
            [],
            (
                "Templates",
                "Sent messages",
                "Uploads",
                "Team members",
            ),
            403,
        ),
        (
            [ORGANISATION_ID],
            (
                "Templates",
                "Sent messages",
                "Uploads",
                "Team members",
                "Usage",
            ),
            200,
        ),
    ],
)
def test_service_user_without_manage_service_permission_can_see_usage_page_when_org_user(
    client_request,
    mocker,
    active_caseworking_user,
    mock_get_annual_usage_for_service,
    mock_get_monthly_usage_for_service,
    mock_get_free_sms_fragment_limit,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_api_keys,
    user_organisations,
    expected_status,
    expected_menu_items,
):
    active_caseworking_user["services"] = [SERVICE_ONE_ID]
    active_caseworking_user["organisations"] = user_organisations
    service = service_json(
        id_=SERVICE_ONE_ID,
        organisation_id=ORGANISATION_ID,
    )
    mocker.patch("app.service_api_client.get_service", return_value={"data": service})
    client_request.login(active_caseworking_user, service=service)
    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )
    assert tuple(item.text.strip() for item in page.select("nav.navigation a")) == expected_menu_items

    client_request.get(
        "main.usage",
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
    return f"{node.func.value.id}.{node.func.attr}"


def get_decorators_for_function(function):
    for node in ast.walk(ast.parse(inspect.getsource(function))):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                yield get_name_of_decorator_from_ast_node(decorator)


SERVICE_ID_ARGUMENT = "service_id"
ORGANISATION_ID_ARGUMENT = "org_id"


def get_routes_and_decorators(argument_name=None):
    import app.main.views_nl as views

    for module_name, module in (
        inspect.getmembers(views) + inspect.getmembers(views.organisations) + inspect.getmembers(views.service_settings)
    ):
        for function_name, function in inspect.getmembers(module):
            if inspect.isfunction(function):
                decorators = list(get_decorators_for_function(function))
                if "main.route" in decorators and (
                    not argument_name or argument_name in inspect.signature(function).parameters.keys()
                ):
                    yield f"{module_name}.{function_name}", decorators


def format_decorators(decorators, indent=8):
    return "\n".join(f"{' ' * indent}@{decorator}" for decorator in decorators)


def test_code_to_extract_decorators_works_with_known_examples():
    assert (
        "templates.choose_template",
        ["main.route", "main.route", "main.route", "main.route", "main.route", "main.route", "user_has_permissions"],
    ) in list(get_routes_and_decorators(SERVICE_ID_ARGUMENT))
    assert (
        "index.organisation_dashboard",
        ["main.route", "user_has_permissions"],
    ) in list(get_routes_and_decorators(ORGANISATION_ID_ARGUMENT))
    assert (
        "platform_admin.platform_admin_search",
        ["main.route", "user_is_platform_admin"],
    ) in list(get_routes_and_decorators())
    assert (
        "branding.letter_branding_request",
        ["main.route", "user_has_permissions"],
    ) in list(get_routes_and_decorators(SERVICE_ID_ARGUMENT))


# TODO: FIXME these are broken because of the routing being changed
def test_routes_have_permissions_decorators():
    for endpoint, decorators in list(get_routes_and_decorators(SERVICE_ID_ARGUMENT)) + list(
        get_routes_and_decorators(ORGANISATION_ID_ARGUMENT)
    ):
        file, function = endpoint.split(".")

        assert "user_is_logged_in" not in decorators, (
            f"@user_is_logged_in used on service or organisation specific endpoint\n"
            f"Use @user_has_permissions() or @user_is_platform_admin only\n"
            f"app/main/views/{file}.py::{function}\n"
        )

        if "user_is_platform_admin" in decorators:
            continue

        assert "user_has_permissions" in decorators, (
            f"Missing @user_has_permissions decorator\n"
            f"Use @user_has_permissions() or @user_is_platform_admin instead\n"
            f"app/main/views/{file}.py::{function}\n"
        )

    for _endpoint, decorators in get_routes_and_decorators():
        assert "login_required" not in decorators, (
            f"@login_required found\n"
            f"For consistency, use @user_is_logged_in() instead (from app.utils)\n"
            f"app/main/views/{file}.py::{function}\n"
        )

        if "user_is_platform_admin" in decorators:
            assert "user_has_permissions" not in decorators, (
                f"@user_has_permissions and @user_is_platform_admin decorating same function\n"
                f"You can only use one of these at a time\n"
                f"app/main/views/{file}.py::{function}\n"
            )
            assert "user_is_logged_in" not in decorators, (
                f"@user_is_logged_in used with @user_is_platform_admin\n"
                f"Use @user_is_platform_admin only\n"
                f"app/main/views_nl/{file}.py::{function}\n"
            )


def test_routes_require_types(client_request):
    partial_param_name_to_type = {
        "_id": "uuid",
        "daily_limit_type": "daily_limit_type",
        "template_type": "template_type",
        "notification_type": "template_type",
        "branding_type": "branding_type",
    }
    for rule in current_app.url_map.iter_rules():
        for param in re.findall("<([^>]*)>", rule.rule):
            if ":" not in param:
                pytest.fail(f"Should be <type:{param}> in {rule.rule}, where type is string, template_type, uuid, etc")
            for partial_param, required_type in partial_param_name_to_type.items():
                if partial_param in param and not param.startswith(f"{required_type}:"):
                    pytest.fail(f"Should be <{required_type}:{param}> in {rule.rule}")
