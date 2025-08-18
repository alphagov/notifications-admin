import uuid
from unittest.mock import ANY, call

import pytest
from flask import url_for
from notifications_python_client.errors import HTTPError

from tests import user_json
from tests.conftest import create_user, normalize_spaces


def test_user_information_page_shows_information_about_user(
    client_request,
    platform_admin_user,
    mocker,
    fake_uuid,
):
    client_request.login(platform_admin_user)
    user_service_one = uuid.uuid4()
    user_service_two = uuid.uuid4()
    user_organisation = uuid.uuid4()
    mocker.patch(
        "app.user_api_client.get_user",
        return_value=user_json(name="Apple Bloom", services=[user_service_one, user_service_two]),
    )

    mocker.patch(
        "app.user_api_client.get_organisations_and_services_for_user",
        return_value={
            "organisations": [
                {"id": user_organisation, "name": "Nature org"},
            ],
            "services": [
                {"id": user_service_one, "name": "Fresh Orchard Juice", "restricted": True},
                {"id": user_service_two, "name": "Nature Therapy", "restricted": False},
            ],
        },
        autospec=True,
    )
    page = client_request.get("main.user_information", user_id=fake_uuid)

    assert normalize_spaces(page.select_one("h1").text) == "Apple Bloom"

    assert [normalize_spaces(p.text) for p in page.select("main p")] == [
        "test@gov.uk",
        "+447700900986",
        "Signs in with a text message code",
        "Last logged in just now",
        "Does not want to receive new features email",
        "Does not want to take part in user research",
    ]

    assert "0 failed login attempts" not in page.text

    assert [normalize_spaces(h2.text) for h2 in page.select("main h2")] == [
        "Organisations",
        "Live services",
        "Trial mode services",
        "Authentication",
        "Preferences",
    ]

    assert [normalize_spaces(a.text) for a in page.select("main li a")] == [
        "Nature org",
        "Nature Therapy",
        "Fresh Orchard Juice",
    ]

    assert "platform admin" not in page.select_one("main").text.lower()


def test_user_information_page_shows_change_auth_type_link(
    client_request, platform_admin_user, api_user_active, mock_get_organisations_and_services_for_user, mocker
):
    client_request.login(platform_admin_user)
    mocker.patch(
        "app.user_api_client.get_user",
        return_value=user_json(id_=api_user_active["id"], name="Apple Bloom", auth_type="sms_auth"),
    )

    page = client_request.get("main.user_information", user_id=api_user_active["id"])
    change_auth_url = url_for("main.change_user_auth", user_id=api_user_active["id"])

    link = page.select_one(f'a[href="{change_auth_url}"]')
    assert normalize_spaces(link.text) == "Change authentication for this user"


def test_user_information_page_doesnt_show_change_auth_type_link_if_user_on_webauthn(
    client_request, platform_admin_user, api_user_active, mock_get_organisations_and_services_for_user, mocker
):
    client_request.login(platform_admin_user)
    mocker.patch(
        "app.user_api_client.get_user",
        side_effect=[
            platform_admin_user,
            user_json(id_=api_user_active["id"], name="Apple Bloom", auth_type="webauthn_auth"),
        ],
    )

    page = client_request.get("main.user_information", user_id=api_user_active["id"])
    change_auth_url = url_for("main.change_user_auth", user_id=api_user_active["id"])

    assert not any(link["href"] == change_auth_url for link in page.select("a"))


@pytest.mark.parametrize("current_auth_type", ["email_auth", "sms_auth"])
def test_change_user_auth_preselects_current_auth_type(
    client_request, platform_admin_user, api_user_active, mocker, current_auth_type
):
    client_request.login(platform_admin_user)

    mocker.patch(
        "app.user_api_client.get_user",
        return_value=user_json(id_=api_user_active["id"], name="Apple Bloom", auth_type=current_auth_type),
    )

    checked_radios = client_request.get(
        "main.change_user_auth",
        user_id=api_user_active["id"],
    ).select(".govuk-radios__item input[checked]")

    assert len(checked_radios) == 1
    assert checked_radios[0]["value"] == current_auth_type


def test_change_user_auth(client_request, platform_admin_user, api_user_active, mocker):
    client_request.login(platform_admin_user)

    mocker.patch(
        "app.user_api_client.get_user",
        return_value=user_json(id_=api_user_active["id"], name="Apple Bloom", auth_type="sms_auth"),
    )

    mock_update = mocker.patch("app.user_api_client.update_user_attribute")

    client_request.post(
        "main.change_user_auth",
        user_id=api_user_active["id"],
        _data={"auth_type": "email_auth"},
        _expected_redirect=url_for("main.user_information", user_id=api_user_active["id"]),
    )

    mock_update.assert_called_once_with(
        api_user_active["id"],
        auth_type="email_auth",
    )


def test_user_information_page_displays_if_there_are_failed_login_attempts(
    client_request,
    platform_admin_user,
    mocker,
    fake_uuid,
):
    client_request.login(platform_admin_user)
    mocker.patch(
        "app.user_api_client.get_user",
        return_value=user_json(name="Apple Bloom", failed_login_count=2),
    )

    mocker.patch(
        "app.user_api_client.get_organisations_and_services_for_user",
        return_value={"organisations": [], "services": []},
        autospec=True,
    )
    page = client_request.get("main.user_information", user_id=fake_uuid)

    assert normalize_spaces(page.select("main p")[-1].text) == "2 failed login attempts"


def test_user_information_page_shows_if_user_is_platform_admin(
    client_request,
    platform_admin_user,
    api_user_active,
    mock_get_organisations_and_services_for_user,
    mocker,
):
    client_request.login(platform_admin_user)
    other_platform_admin_user = create_user(platform_admin=True, id=uuid.uuid4())
    mocker.patch("app.user_api_client.get_user", return_value=other_platform_admin_user)

    page = client_request.get("main.user_information", user_id=other_platform_admin_user["id"])

    assert normalize_spaces(page.select_one(".govuk-tag").text) == "Platform admin"
    assert normalize_spaces(page.select_one("main p a").text) == "Remove"
    assert page.select_one("main p a")["href"] == url_for(
        "main.remove_platform_admin",
        user_id=other_platform_admin_user["id"],
    )


def test_remove_platform_admin_prompts_for_confirmation(
    client_request,
    platform_admin_user,
    api_user_active,
    mock_get_organisations_and_services_for_user,
):
    client_request.login(platform_admin_user)
    page = client_request.get("main.remove_platform_admin", user_id=api_user_active["id"])

    assert normalize_spaces(page.select_one("div.banner-dangerous").text) == (
        "Are you sure you want to remove platform admin from this user? Yes, remove"
    )
    assert page.select_one("div.banner-dangerous form[method=post] button[type=submit]")


@pytest.mark.parametrize(
    "mobile_number, expected_auth_type",
    (
        ("12345", "sms_auth"),
        (None, "email_auth"),
    ),
)
def test_remove_platform_admin_removes_user_admin_privilege_and_changes_user_auth(
    client_request,
    platform_admin_user,
    fake_uuid,
    mock_get_organisations_and_services_for_user,
    mock_update_user_attribute,
    mobile_number,
    expected_auth_type,
    mock_events,
):
    platform_admin_user["mobile_number"] = mobile_number
    client_request.login(platform_admin_user)
    client_request.post("main.remove_platform_admin", user_id=fake_uuid)

    mock_update_user_attribute.assert_called_once_with(
        platform_admin_user["id"],
        platform_admin=False,
        auth_type=expected_auth_type,
    )
    assert mock_events.call_args_list == [call("remove_platform_admin", ANY)]


def test_user_information_page_shows_archive_link_for_active_users(
    client_request,
    platform_admin_user,
    api_user_active,
    mock_get_organisations_and_services_for_user,
):
    client_request.login(platform_admin_user)
    page = client_request.get("main.user_information", user_id=api_user_active["id"])
    archive_url = url_for("main.archive_user", user_id=api_user_active["id"])

    link = page.select_one(f'a[href="{archive_url}"]')
    assert normalize_spaces(link.text) == "Archive user"


def test_user_information_page_does_not_show_archive_link_for_inactive_users(
    client_request,
    platform_admin_user,
    mock_get_organisations_and_services_for_user,
    mocker,
):
    inactive_user_id = uuid.uuid4()
    inactive_user = user_json(id_=inactive_user_id, state="inactive")
    client_request.login(platform_admin_user)
    mocker.patch("app.user_api_client.get_user", side_effect=[platform_admin_user, inactive_user])

    page = client_request.get("main.user_information", user_id=inactive_user_id)

    assert not any(a["href"] == url_for("main.archive_user", user_id=inactive_user_id) for a in page.select("a"))


@pytest.mark.skip(reason="[NOTIFYNL] [FIXME] 'banner' is undefined")
def test_archive_user_prompts_for_confirmation(
    client_request,
    platform_admin_user,
    api_user_active,
    mock_get_organisations_and_services_for_user,
):
    client_request.login(platform_admin_user)
    page = client_request.get("main.archive_user", user_id=api_user_active["id"])

    assert "Are you sure you want to archive this user?" in page.select_one("div.banner-dangerous").text


def test_archive_user_posts_to_user_client(
    client_request,
    platform_admin_user,
    api_user_active,
    mocker,
    mock_events,
):
    mock_user_client = mocker.patch("app.user_api_client.post")

    client_request.login(platform_admin_user)
    client_request.post(
        "main.archive_user",
        user_id=api_user_active["id"],
        _expected_redirect=url_for(
            "main.user_information",
            user_id=api_user_active["id"],
        ),
    )

    mock_user_client.assert_called_once_with(f"/user/{api_user_active['id']}/archive", data=None)

    assert mock_events.called


@pytest.mark.skip(reason="[NOTIFYNL] [FIXME] 'banner' is undefined")
def test_archive_user_shows_error_message_if_user_cannot_be_archived(
    client_request,
    platform_admin_user,
    api_user_active,
    mocker,
    mock_get_non_empty_organisations_and_services_for_user,
):
    mocker.patch(
        "app.user_api_client.post",
        side_effect=HTTPError(
            response=mocker.Mock(
                status_code=400,
                json={
                    "result": "error",
                    "message": "User can’t be removed from a service - check all services have another "
                    "team member with manage_settings",
                },
            ),
            message="User can’t be removed from a service - check all services have another team member "
            "with manage_settings",
        ),
    )

    client_request.login(platform_admin_user)
    page = client_request.post(
        "main.archive_user",
        user_id=api_user_active["id"],
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Platform admin user"
    assert (
        normalize_spaces(page.select_one(".banner-dangerous").text)
        == "User can’t be removed from a service - check all services have another team member with manage_settings"
    )


def test_archive_user_does_not_create_event_if_user_client_raises_unexpected_exception(
    client_request,
    platform_admin_user,
    api_user_active,
    mocker,
    mock_events,
):
    mocker.patch("app.main.views_nl.find_users.user_api_client.archive_user", side_effect=ValueError())
    with pytest.raises(ValueError):
        client_request.login(platform_admin_user)
        client_request.post(
            "main.archive_user",
            user_id=api_user_active["id"],
        )

    assert not mock_events.called
