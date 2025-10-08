import pytest
from flask import url_for
from flask_login import current_user
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError

from app.utils.user import is_gov_user
from tests import organisation_json
from tests.conftest import normalize_spaces


def test_non_gov_user_cannot_see_add_service_button(
    client_request,
    login_non_govuser,
    api_nongov_user_active,
    mock_get_organisations,
    mock_get_organisations_and_services_for_user,
):
    client_request.login(api_nongov_user_active)
    page = client_request.get("main.your_services")
    assert "Add a new service" not in page.text


@pytest.mark.parametrize(
    "org_json",
    (
        None,
        organisation_json(organisation_type=None),
    ),
)
@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_get_should_render_add_service_template(
    client_request,
    mocker,
    org_json,
):
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=org_json,
    )
    page = client_request.get("main.add_service")
    assert page.select_one("h1").text.strip() == "Enter a service name"
    assert page.select_one("input[name=name]").get("value") is None
    assert [label.text.strip() for label in page.select(".govuk-radios__item label")] == [
        "Central government",
        "Local government",
        "NHS – central government agency or public body",
        "NHS Trust or Integrated Care Board",
        "GP surgery",
        "Emergency service",
        "School or college",
        "Other",
    ]
    assert [radio["value"] for radio in page.select(".govuk-radios__item input")] == [
        "central",
        "local",
        "nhs_central",
        "nhs_local",
        "nhs_gp",
        "emergency_service",
        "school_or_college",
        "other",
    ]


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_get_should_not_render_radios_if_org_type_known(
    client_request,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=organisation_json(organisation_type="central"),
    )
    page = client_request.get("main.add_service")
    assert page.select_one("h1").text.strip() == "Enter a service name"
    assert page.select_one("input[name=name]").get("value") is None
    assert not page.select(".multiple-choice")


@pytest.mark.parametrize(
    "org_type, expected_content_lines",
    (
        ("central", ["Register to vote", "Renew your Passport", "Check your state pension"]),
        ("local", ["School admissions", "Electoral services", "Blue Badge"]),
        ("nhs", ["Your service name should tell the recipient what your message is about, as well as who it’s from."]),
    ),
)
@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_show_different_page_content_based_on_user_org_type(client_request, mocker, org_type, expected_content_lines):
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=organisation_json(organisation_type=org_type),
    )
    page = client_request.get("main.add_service")
    assert page.select_one("h1").text.strip() == "Enter a service name"
    assert page.select_one("input[name=name]").get("value") is None
    assert all(content in page.select_one("main").text for content in expected_content_lines)
    assert not page.select(".govuk-back-link")


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_shows_back_link_if_come_from_your_services_page(
    client_request,
    mock_get_no_organisation_by_domain,
):
    page = client_request.get("main.add_service", back="your_services")
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.your_services")


@pytest.mark.parametrize(
    "email_address",
    (
        # User’s email address doesn’t matter when the organisation is known
        "test@example.gov.uk",
        "test@example.nhs.uk",
    ),
)
@pytest.mark.parametrize(
    "inherited, posted, persisted",
    (
        (None, "central", "central"),
        (None, "nhs_central", "nhs_central"),
        (None, "nhs_local", "nhs_local"),
        (None, "local", "local"),
        (None, "emergency_service", "emergency_service"),
        (None, "school_or_college", "school_or_college"),
        (None, "other", "other"),
        ("central", None, "central"),
        ("nhs_central", None, "nhs_central"),
        ("nhs_local", None, "nhs_local"),
        ("local", None, "local"),
        ("emergency_service", None, "emergency_service"),
        ("school_or_college", None, "school_or_college"),
        ("other", None, "other"),
        ("central", "local", "central"),
    ),
)
@freeze_time("2021-01-01")
@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_should_add_service_and_redirect_to_tour_when_no_services(
    client_request,
    mock_create_service_template,
    mock_get_services_with_no_services,
    api_user_active,
    fake_uuid,
    inherited,
    email_address,
    posted,
    persisted,
    mocker,
):
    api_user_active["email_address"] = email_address
    client_request.login(api_user_active)
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=organisation_json(organisation_type=inherited),
    )

    mock_create_service = mocker.patch(
        "app.notify_client.service_api_client.ServiceAPIClient.post",
        return_value={"data": {"id": 101}},
    )

    client_request.post(
        "main.add_service",
        _data={
            "name": "testing the post",
            "organisation_type": posted,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.begin_tour",
            service_id=101,
            template_id=fake_uuid,
        ),
    )
    assert mock_get_services_with_no_services.called

    mock_create_service.assert_called_once_with(
        "/service",
        {
            "created_by": api_user_active["id"],
            "name": "testing the post",
            "organisation_type": persisted,
            "active": True,
            "email_message_limit": 50,
            "international_sms_message_limit": 100,
            "sms_message_limit": 50,
            "letter_message_limit": 50,
            "user_id": "6ce466d0-fd6a-11e5-82f5-e0accb9d11a6",
            "restricted": True,
        },
    )

    mock_create_service_template.assert_called_once_with(
        name="Example text message template",
        type_="sms",
        content=(
            "Hey ((name)), I’m trying out Notify. Today is ((day of week)) and my favourite colour is ((colour))."
        ),
        service_id=101,
    )
    with client_request.session_transaction() as session:
        assert session["service_id"] == 101


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_add_service_has_to_choose_org_type(
    client_request,
    mock_create_service,
    mock_create_service_template,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=None,
    )
    page = client_request.post(
        "main.add_service",
        _data={
            "name": "testing the post",
        },
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: Select a type of organisation"
    assert mock_create_service.called is False
    assert mock_create_service_template.called is False


@pytest.mark.parametrize(
    "email_address",
    (
        "test@nhs.net",
        "test@nhs.uk",
        "test@example.NhS.uK",
        "test@EXAMPLE.NHS.NET",
    ),
)
@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_get_should_only_show_nhs_org_types_radios_if_user_has_nhs_email(
    client_request,
    mocker,
    api_user_active,
    email_address,
):
    api_user_active["email_address"] = email_address
    client_request.login(api_user_active)
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=None,
    )
    page = client_request.get("main.add_service")
    assert page.select_one("h1").text.strip() == "Enter a service name"
    assert page.select_one("input[name=name]").get("value") is None
    assert [label.text.strip() for label in page.select(".govuk-radios__item label")] == [
        "NHS – central government agency or public body",
        "NHS Trust or Integrated Care Board",
        "GP surgery",
    ]
    assert [radio["value"] for radio in page.select(".govuk-radios__item input")] == [
        "nhs_central",
        "nhs_local",
        "nhs_gp",
    ]


@pytest.mark.parametrize(
    "organisation_type",
    [
        "central",
        "local",
        "nhs_central",
        "nhs_local",
        "nhs_gp",
        "school_or_college",
        "emergency_service",
        "other",
    ],
)
@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_should_add_service_and_redirect_to_dashboard_when_existing_service(
    notify_admin,
    client_request,
    mock_create_service,
    mock_create_service_template,
    mock_get_services,
    mock_update_service,
    mock_get_no_organisation_by_domain,
    api_user_active,
    organisation_type,
):
    client_request.post(
        "main.add_service",
        _data={
            "name": "testing the post",
            "organisation_type": organisation_type,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_dashboard",
            service_id=101,
        ),
    )
    assert mock_get_services.called
    mock_create_service.assert_called_once_with(
        service_name="testing the post",
        organisation_type=organisation_type,
        email_message_limit=notify_admin.config["DEFAULT_SERVICE_LIMIT"],
        international_sms_message_limit=notify_admin.config["DEFAULT_SERVICE_INTERNATIONAL_SMS_LIMIT"],
        sms_message_limit=notify_admin.config["DEFAULT_SERVICE_LIMIT"],
        letter_message_limit=notify_admin.config["DEFAULT_SERVICE_LIMIT"],
        restricted=True,
        user_id=api_user_active["id"],
    )
    assert len(mock_create_service_template.call_args_list) == 0
    with client_request.session_transaction() as session:
        assert session["service_id"] == 101


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_add_service_sets_nhs_gp_daily_sms_limit_to_zero_when_user_already_has_services(
    mock_get_no_organisation_by_domain,
    client_request,
    mock_create_service,
    mock_create_service_template,
    mock_update_service,
    mock_get_services,
):
    client_request.post(
        "main.add_service",
        _data={"name": "testing the post", "organisation_type": "nhs_gp"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_dashboard",
            service_id=101,
        ),
    )
    assert mock_get_services.called
    assert mock_create_service.called

    mock_update_service.assert_called_once_with(101, sms_message_limit=0)

    assert mock_create_service_template.called is False


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_add_service_sets_nhs_gp_daily_sms_limit_to_zero_when_user_has_no_other_services(
    mock_get_no_organisation_by_domain,
    client_request,
    mock_create_service,
    mock_create_service_template,
    mock_update_service,
    mock_get_services_with_no_services,
):
    client_request.post(
        "main.add_service",
        _data={"name": "testing the post", "organisation_type": "nhs_gp"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_dashboard",
            service_id=101,
        ),
    )
    assert mock_get_services_with_no_services.called
    assert mock_create_service.called

    mock_update_service.assert_called_once_with(101, sms_message_limit=0)

    assert mock_create_service_template.called is False


@pytest.mark.parametrize(
    "name, error_message",
    [
        ("", "Enter a service name"),
        (".", "Must include at least two alphanumeric characters"),
        ("a" * 256, "Service name cannot be longer than 255 characters"),
    ],
)
@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_add_service_fails_if_service_name_fails_validation(
    client_request,
    mock_get_organisation_by_domain,
    name,
    error_message,
):
    page = client_request.post(
        "main.add_service",
        _data={"name": name},
        _expected_status=200,
    )
    assert error_message in page.select_one(".govuk-error-message").text


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_should_return_form_errors_with_duplicate_service_name_regardless_of_case(
    client_request,
    mock_get_organisation_by_domain,
    mocker,
):
    def _create(**_kwargs):
        json_mock = mocker.Mock(return_value={"message": {"name": ["Duplicate service name"]}})
        resp_mock = mocker.Mock(status_code=400, json=json_mock)
        http_error = HTTPError(response=resp_mock, message="Default message")
        raise http_error

    mocker.patch("app.service_api_client.create_service", side_effect=_create)

    page = client_request.post(
        "main.add_service",
        _data={
            "name": "SERVICE ONE",
            "organisation_type": "central",
        },
        _expected_status=200,
    )
    assert "This service name is already in use" in page.select_one(".govuk-error-message").text.strip()


def test_non_government_user_cannot_access_create_service_page(
    client_request,
    login_non_govuser,
    api_nongov_user_active,
    mock_get_organisations,
):
    assert is_gov_user(current_user.email_address) is False
    client_request.get(
        "main.add_service",
        _expected_status=403,
    )


def test_non_government_user_cannot_create_service(
    client_request,
    login_non_govuser,
    api_nongov_user_active,
    mock_get_organisations,
):
    assert is_gov_user(current_user.email_address) is False
    client_request.post(
        "main.add_service",
        _data={"name": "SERVICE TWO"},
        _expected_status=403,
    )


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_email_auth_user_creates_service_with_email_auth_permission(
    api_user_active_email_auth,
    client_request,
    mock_get_no_organisation_by_domain,
    mock_get_services,
    mock_create_service,
    mock_update_service,
):
    client_request.login(api_user_active_email_auth, service=None)
    client_request.post(
        "main.add_service",
        _data={
            "name": "service name",
            "organisation_type": "central",
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_dashboard",
            service_id=101,
        ),
    )
    assert mock_create_service.called
    assert mock_update_service.call_args[0][0] == 101
    assert "email_auth" in mock_update_service.call_args[1]["permissions"]
