from io import BytesIO
from unittest import mock
from unittest.mock import call

import pytest
from flask import url_for
from notifications_python_client.errors import HTTPError

from app.models.branding import get_insignia_asset_path
from tests.conftest import create_email_branding, normalize_spaces


def test_email_branding_page_shows_full_branding_list(client_request, platform_admin_user, mock_get_all_email_branding):
    client_request.login(platform_admin_user)
    page = client_request.get(".email_branding")

    links = page.select(".browse-list-item a")
    brand_names = [normalize_spaces(link.text) for link in links]
    hrefs = [link["href"] for link in links]

    assert normalize_spaces(page.select_one("h1").text) == "Email branding"

    assert page.select(".govuk-grid-column-three-quarters a")[-2]["href"] == url_for(
        "main.platform_admin_create_email_branding"
    )
    assert page.select(".govuk-grid-column-three-quarters a")[-1]["href"] == url_for(
        "main.create_email_branding_government_identity_logo"
    )

    assert brand_names == [
        "org 1",
        "org 2",
        "org 3",
        "org 4",
        "org 5",
    ]
    assert hrefs == [
        url_for(".platform_admin_view_email_branding", branding_id=1),
        url_for(".platform_admin_view_email_branding", branding_id=2),
        url_for(".platform_admin_view_email_branding", branding_id=3),
        url_for(".platform_admin_view_email_branding", branding_id=4),
        url_for(".platform_admin_view_email_branding", branding_id=5),
    ]


@pytest.mark.parametrize(
    "user_fixture, expected_response_status", (("api_user_active_email_auth", 403), ("platform_admin_user", 200))
)
def test_view_email_branding_requires_platform_admin(
    client_request,
    mock_get_email_branding,
    user_fixture,
    expected_response_status,
    request,
    fake_uuid,
    mocker,
):
    mocker.patch(
        "app.email_branding_client.get_orgs_and_services_associated_with_branding",
    )
    user = request.getfixturevalue(user_fixture)
    client_request.login(user)
    client_request.get(
        ".platform_admin_view_email_branding", branding_id=fake_uuid, _expected_status=expected_response_status
    )


def test_view_email_branding_with_services_but_no_orgs(
    client_request,
    platform_admin_user,
    mock_get_email_branding,
    fake_uuid,
    mock_get_orgs_and_services_associated_with_branding_no_orgs,
):
    client_request.login(platform_admin_user)

    page = client_request.get(".platform_admin_view_email_branding", branding_id=fake_uuid)

    assert page.select_one(".hint").text.strip() == "No organisations use this branding as their default."

    list_of_service_links = page.select(".browse-list-item")

    link_1 = list_of_service_links[0].select_one("a")
    assert link_1.text.strip() == "service 1"
    assert link_1["href"] == url_for(".service_settings", service_id="1234")

    link_2 = list_of_service_links[1].select_one("a")
    assert link_2.text.strip() == "service 2"
    assert link_2["href"] == url_for(".service_settings", service_id="5678")


def test_view_email_branding_with_org_but_no_services(
    client_request,
    platform_admin_user,
    mock_get_email_branding,
    fake_uuid,
    mock_get_orgs_and_services_associated_with_branding_no_services,
):
    client_request.login(platform_admin_user)

    page = client_request.get(".platform_admin_view_email_branding", branding_id=fake_uuid)

    assert page.select_one(".hint").text.strip() == "No services use this branding."

    list_of_organisation_links = page.select(".browse-list-item")

    link_1 = list_of_organisation_links[0].select_one("a")
    assert link_1.text.strip() == "organisation 1"
    assert link_1["href"] == url_for(".organisation_settings", org_id="1234")


@pytest.mark.parametrize(
    "created_at, updated_at", [("2022-12-06T09:59:56.000000Z", "2023-01-20T11:59:56.000000Z"), (None, None)]
)
def test_view_email_branding_shows_created_by_and_helpful_dates_if_available(
    client_request,
    platform_admin_user,
    fake_uuid,
    mock_get_orgs_and_services_associated_with_branding_empty,
    mocker,
    created_at,
    updated_at,
):
    client_request.login(platform_admin_user)

    def _get_email_branding(id):
        return create_email_branding(
            id,
            non_standard_values={
                "created_by": "1234-5678-abcd-efgh",
                "created_at": created_at,
                "updated_at": updated_at,
            },
        )

    mocker.patch("app.models.branding.email_branding_client.get_email_branding", side_effect=_get_email_branding)

    user = {"id": "1234-5678-abcd-efgh", "name": "Arwa Suren"}
    mocker.patch("app.models.branding.user_api_client.get_user", return_value=user)

    page = client_request.get(".platform_admin_view_email_branding", branding_id=fake_uuid)

    created_by_link = page.select("main .govuk-body > a")[0]
    assert created_by_link.text.strip() == user["name"]
    assert created_by_link["href"] == url_for(".user_information", user_id=user["id"])

    if created_at:
        assert "on Tuesday 06 December 2022" in page.select("p")[-2].text

    if updated_at:
        assert "on Friday 20 January 2023" in page.select("p")[-1].text


def test_view_email_branding_bottom_links(
    client_request,
    platform_admin_user,
    mock_get_email_branding,
    fake_uuid,
    mock_get_orgs_and_services_associated_with_branding_empty,
):
    client_request.login(platform_admin_user)

    page = client_request.get(".platform_admin_view_email_branding", branding_id=fake_uuid)

    bottom_links = page.select(".page-footer-link")

    edit_link = bottom_links[0].select_one("a")
    assert edit_link.text.strip() == "Edit this branding"
    assert edit_link["href"] == url_for(".platform_admin_update_email_branding", branding_id=fake_uuid)

    archive_link = bottom_links[1].select_one("a")
    assert archive_link.text.strip() == "Delete this branding"
    assert archive_link["href"] == url_for(".platform_admin_confirm_archive_email_branding", branding_id=fake_uuid)


def test_edit_email_branding_shows_the_correct_branding_info(
    client_request, platform_admin_user, mock_get_email_branding, fake_uuid
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        ".platform_admin_update_email_branding",
        branding_id=fake_uuid,
    )

    assert page.select_one("#logo-img > img")["src"].endswith("/example.png")
    assert page.select_one("#name").attrs.get("value") == "Organisation name"
    assert page.select_one("#file").attrs.get("accept") == ".png"
    assert page.select_one("#text").attrs.get("value") == "Organisation text"
    assert page.select_one("#colour").attrs.get("value") == "f00"


def test_create_email_branding_does_not_show_any_branding_info(client_request, platform_admin_user):
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.platform_admin_create_email_branding",
    )

    assert page.select_one("#logo-img > img") is None
    assert page.select_one("#name").attrs.get("value") is None
    assert page.select_one("#file").attrs.get("accept") == ".png"
    assert page.select_one("#text").attrs.get("value") is None
    assert page.select_one("#colour").attrs.get("value") is None


def test_create_email_branding_can_be_populated_from_querystring(client_request, platform_admin_user):
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.platform_admin_create_email_branding",
        name="Example name",
        text="Example text",
        colour="Example colour",
        brand_type="both",
    )

    assert page.select_one("#name")["value"] == "Example name"
    assert page.select_one("#text")["value"] == "Example text"
    assert page.select_one("#colour")["value"] == "Example colour"
    assert page.select_one("#brand_type input")["value"] == "both"


@pytest.mark.parametrize(
    "extra_kwargs, expected_backlink",
    (
        ({}, "/email-branding"),
        (
            {"back": "government-identity", "government_identity": "HM Government"},
            "/email-branding/create-government-identity/colour?filename=HM+Government",
        ),
    ),
)
def test_create_email_branding_backlinks(client_request, platform_admin_user, extra_kwargs, expected_backlink):
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.platform_admin_create_email_branding",
        name="Example name",
        text="Example text",
        colour="Example colour",
        brand_type="both",
        **extra_kwargs,
    )

    assert page.select_one("a.govuk-back-link")["href"] == expected_backlink


def test_create_new_email_branding_without_logo(
    client_request,
    platform_admin_user,
    mocker,
    fake_uuid,
    mock_create_email_branding,
):
    data = {
        "logo": None,
        "colour": "#ff0000",
        "text": "new text",
        "name": "new name",
        "brand_type": "org",
    }

    mock_save_temporary = mocker.patch("app.main.views.email_branding.logo_client.save_temporary_logo")

    client_request.login(platform_admin_user)
    client_request.post(
        "main.platform_admin_create_email_branding",
        _content_type="multipart/form-data",
        _data=data,
    )

    assert mock_create_email_branding.called
    assert mock_create_email_branding.call_args == call(
        logo=data["logo"],
        name=data["name"],
        alt_text=None,
        text=data["text"],
        colour=data["colour"],
        brand_type=data["brand_type"],
        created_by_id=fake_uuid,
    )
    assert mock_save_temporary.call_args_list == []


def test_create_new_email_branding_with_unique_name_conflict(
    client_request,
    platform_admin_user,
    mocker,
):
    data = {"logo": None, "colour": "#ff0000", "text": "new text", "name": "new name", "brand_type": "org"}

    client_request.login(platform_admin_user)

    mock_create_email_branding = mocker.patch("app.email_branding_client.create_email_branding")
    response_mock = mock.Mock()
    response_mock.status_code = 400
    response_mock.json.return_value = {"message": {"name": ["An email branding with that name already exists."]}}
    mock_create_email_branding.side_effect = HTTPError(response=response_mock)
    resp = client_request.post(
        "main.platform_admin_create_email_branding",
        _content_type="multipart/form-data",
        _data=data,
        _expected_status=400,
    )

    assert "An email branding with that name already exists." in resp.text


def test_create_email_branding_requires_a_name_when_submitting_logo_details(
    client_request,
    mock_create_email_branding,
    platform_admin_user,
):
    data = {
        "operation": "email-branding-details",
        "logo": "",
        "colour": "#ff0000",
        "text": "new text",
        "name": "",
        "brand_type": "org",
    }
    client_request.login(platform_admin_user)
    page = client_request.post(
        "main.platform_admin_create_email_branding",
        _content_type="multipart/form-data",
        _data=data,
        _expected_status=400,
    )

    assert page.select_one(".govuk-error-message").text.strip() == "Error: Enter a name for the branding"
    assert mock_create_email_branding.called is False


def test_create_email_branding_does_not_require_a_name_when_uploading_a_file(
    client_request,
    mocker,
    platform_admin_user,
):
    mocker.patch("app.main.views.email_branding.logo_client.save_temporary_logo", return_value="temp_filename")
    mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    data = {
        "file": (BytesIO(b""), "test.png"),
        "colour": "",
        "text": "",
        "name": "",
        "brand_type": "org",
    }
    client_request.login(platform_admin_user)
    page = client_request.post(
        "main.platform_admin_create_email_branding",
        _content_type="multipart/form-data",
        _data=data,
        _follow_redirects=True,
    )

    assert not page.select_one(".govuk-error-message")


@pytest.mark.parametrize(
    "scan_result, expected_status_code",
    (
        (True, 302),
        (False, 400),
    ),
)
def test_create_email_branding_calls_antivirus_scan(
    client_request,
    mocker,
    platform_admin_user,
    scan_result,
    expected_status_code,
):
    mocker.patch("app.main.views.email_branding.logo_client.save_temporary_logo", return_value="temp_filename")
    mock_antivirus = mocker.patch("app.extensions.antivirus_client.scan", return_value=scan_result)
    data = {
        "file": (BytesIO(b""), "test.png"),
        "colour": "",
        "text": "",
        "name": "",
        "brand_type": "org",
    }
    client_request.login(platform_admin_user)
    client_request.post(
        "main.platform_admin_create_email_branding",
        _content_type="multipart/form-data",
        _data=data,
        _expected_status=expected_status_code,
    )

    assert mock_antivirus.call_count == 1


@pytest.mark.parametrize(
    "text,alt_text",
    [
        ("foo", ""),
        ("", "bar"),
    ],
)
def test_create_new_email_branding_when_branding_saved(
    client_request,
    mocker,
    platform_admin_user,
    mock_create_email_branding,
    fake_uuid,
    text,
    alt_text,
    logo_client,
):
    data = {
        "operation": "email-branding-details",
        "logo_key": "test.png",
        "colour": "#ff0000",
        "text": text,
        "alt_text": alt_text,
        "name": "new name",
        "brand_type": "org_banner",
    }

    mocker.patch("app.main.views.email_branding.logo_client.save_permanent_logo", return_value="email/test.png")

    client_request.login(platform_admin_user)
    client_request.post(
        "main.platform_admin_create_email_branding",
        logo_key=data["logo_key"],
        _content_type="multipart/form-data",
        _data={
            "colour": data["colour"],
            "name": data["name"],
            "text": data["text"],
            "alt_text": data["alt_text"],
            "cdn_url": "https://static-logos.cdn.com",
            "brand_type": data["brand_type"],
        },
    )

    assert mock_create_email_branding.called
    assert mock_create_email_branding.call_args == call(
        logo="email/test.png",
        name=data["name"],
        alt_text=data["alt_text"],
        text=data["text"],
        colour=data["colour"],
        brand_type=data["brand_type"],
        created_by_id=fake_uuid,
    )


def test_create_email_branding_shows_error_with_neither_alt_text_and_text(
    client_request,
    mock_create_email_branding,
    platform_admin_user,
):
    data = {
        "operation": "email-branding-details",
        "logo": "test.png",
        "colour": "#ff0000",
        "text": "",
        "alt_text": "",
        "name": "some name",
        "brand_type": "org_banner",
    }

    client_request.login(platform_admin_user)
    response = client_request.post("main.platform_admin_create_email_branding", _data=data, _expected_status=400)
    assert response.select_one("#text-error") is None
    assert normalize_spaces(response.select_one("#alt_text-error").text) == "Error: Enter alt text for your logo"
    assert not mock_create_email_branding.called


def test_create_email_branding_shows_error_with_both_alt_text_and_text(
    client_request,
    mock_create_email_branding,
    platform_admin_user,
):
    data = {
        "operation": "email-branding-details",
        "logo": "test.png",
        "colour": "#ff0000",
        "text": "some text",
        "alt_text": "some alt_text",
        "name": "some name",
        "brand_type": "org_banner",
    }

    client_request.login(platform_admin_user)
    response = client_request.post("main.platform_admin_create_email_branding", _data=data, _expected_status=400)
    assert response.select_one("#text-error") is None
    assert (
        normalize_spaces(response.select_one("#alt_text-error").text)
        == "Error: Alt text must be empty if you have already entered logo text"
    )
    assert not mock_create_email_branding.called


def test_update_existing_branding(
    client_request,
    platform_admin_user,
    mocker,
    fake_uuid,
    mock_get_email_branding,
    mock_update_email_branding,
):
    data = {
        "logo": "test.png",
        "colour": "#0000ff",
        "text": "new text",
        "name": "new name",
        "brand_type": "both",
        "updated_by_id": fake_uuid,
    }

    mocker.patch("app.main.views.email_branding.logo_client.save_permanent_logo", return_value="email/test.png")
    mock_create_update_email_branding_event = mocker.patch("app.main.views.email_branding.Events.update_email_branding")

    client_request.login(platform_admin_user)
    client_request.post(
        ".platform_admin_update_email_branding",
        logo_key="email/test.png",
        branding_id=fake_uuid,
        _content_type="multipart/form-data",
        _data={
            "colour": data["colour"],
            "name": data["name"],
            "alt_text": "",
            "text": data["text"],
            "cdn_url": "https://static-logos.cdn.com",
            "brand_type": data["brand_type"],
        },
        _expected_redirect=url_for(
            ".platform_admin_view_email_branding",
            branding_id=fake_uuid,
        ),
    )

    assert mock_update_email_branding.called
    assert mock_update_email_branding.call_args == call(
        branding_id=fake_uuid,
        logo="email/test.png",
        name=data["name"],
        alt_text="",
        text=data["text"],
        colour=data["colour"],
        brand_type=data["brand_type"],
        updated_by_id=data["updated_by_id"],
    )
    assert mock_create_update_email_branding_event.call_args_list == [
        mocker.call(
            email_branding_id=fake_uuid,
            updated_by_id=fake_uuid,
            old_email_branding=mock_get_email_branding(fake_uuid)["email_branding"],
        )
    ]


def test_update_existing_branding_does_not_reupload_logo_if_unchanged(
    client_request,
    platform_admin_user,
    mocker,
    fake_uuid,
    mock_get_email_branding,
    mock_update_email_branding,
):
    data = {
        "logo": "test.png",
        "colour": "#0000ff",
        "text": "new text",
        "name": "new name",
        "brand_type": "both",
        "updated_by_id": fake_uuid,
    }

    mock_save_permanent = mocker.patch("app.main.views.email_branding.logo_client.save_permanent_logo")
    mocker.patch("app.main.views.email_branding.Events.update_email_branding")

    client_request.login(platform_admin_user)
    client_request.post(
        ".platform_admin_update_email_branding",
        branding_id=fake_uuid,
        _content_type="multipart/form-data",
        _data={
            "colour": data["colour"],
            "name": data["name"],
            "alt_text": "",
            "text": data["text"],
            "cdn_url": "https://static-logos.cdn.com",
            "brand_type": data["brand_type"],
        },
    )

    assert mock_update_email_branding.called
    assert mock_update_email_branding.call_args == call(
        branding_id=fake_uuid,
        logo="example.png",
        name=data["name"],
        alt_text="",
        text=data["text"],
        colour=data["colour"],
        brand_type=data["brand_type"],
        updated_by_id=data["updated_by_id"],
    )
    assert not mock_save_permanent.called


def test_update_email_branding_shows_error_with_neither_alt_text_and_text(
    client_request,
    mocker,
    mock_get_email_branding,
    mock_update_email_branding,
    platform_admin_user,
    fake_uuid,
):
    data = {
        "operation": "email-branding-details",
        "logo": "test.png",
        "colour": "#ff0000",
        "text": "",
        "alt_text": "",
        "name": "some name",
        "brand_type": "org_banner",
    }

    mocker.patch("app.main.views.email_branding.logo_client.save_permanent_logo")

    client_request.login(platform_admin_user)
    response = client_request.post(
        "main.platform_admin_update_email_branding", branding_id=fake_uuid, _data=data, _expected_status=400
    )
    assert response.select_one("#text-error") is None
    assert normalize_spaces(response.select_one("#alt_text-error").text) == "Error: Enter alt text for your logo"
    assert not mock_update_email_branding.called


def test_update_email_branding_shows_error_with_both_alt_text_and_text(
    client_request, mocker, mock_get_email_branding, mock_update_email_branding, platform_admin_user, fake_uuid
):
    data = {
        "operation": "email-branding-details",
        "logo": "test.png",
        "colour": "#ff0000",
        "text": "some text",
        "alt_text": "some alt_text",
        "name": "some name",
        "brand_type": "org_banner",
    }

    mocker.patch("app.main.views.email_branding.logo_client.save_permanent_logo")

    client_request.login(platform_admin_user)
    response = client_request.post(
        "main.platform_admin_update_email_branding", branding_id=fake_uuid, _data=data, _expected_status=400
    )
    assert response.select_one("#text-error") is None
    assert (
        normalize_spaces(response.select_one("#alt_text-error").text)
        == "Error: Alt text must be empty if you have already entered logo text"
    )
    assert not mock_update_email_branding.called


def test_update_email_branding_with_unique_name_conflict(
    client_request,
    platform_admin_user,
    mocker,
    fake_uuid,
    mock_get_email_branding,
):
    data = {
        "operation": "email-branding-details",
        "logo": None,
        "colour": "#ff0000",
        "text": "new text",
        "alt_text": "",
        "name": "new name",
        "brand_type": "org",
    }

    client_request.login(platform_admin_user)

    mocker.patch("app.main.views.email_branding.logo_client.save_permanent_logo")
    mock_update_email_branding = mocker.patch("app.email_branding_client.update_email_branding")
    response_mock = mock.Mock()
    response_mock.status_code = 400
    response_mock.json.return_value = {"message": {"name": ["An email branding with that name already exists."]}}
    mock_update_email_branding.side_effect = HTTPError(response=response_mock)
    resp = client_request.post(
        ".platform_admin_update_email_branding",
        branding_id=fake_uuid,
        _content_type="multipart/form-data",
        _data=data,
        _expected_status=400,
    )

    assert (
        normalize_spaces(resp.select_one("#name-error").text)
        == "Error: An email branding with that name already exists."
    )


def test_platform_admin_confirm_archive_email_branding(
    client_request,
    platform_admin_user,
    mock_get_email_branding,
    fake_uuid,
    mock_get_orgs_and_services_associated_with_branding_empty,
):
    client_request.login(platform_admin_user)

    page = client_request.get(".platform_admin_confirm_archive_email_branding", branding_id=fake_uuid)

    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "Are you sure you want to delete this email branding? Yes, delete"
    )
    assert "action" not in page.select_one(".banner-dangerous form")
    assert page.select_one(".banner-dangerous form")["method"] == "post"


def test_platform_admin_confirm_archive_email_branding_that_is_in_use(
    client_request,
    platform_admin_user,
    mock_get_email_branding,
    fake_uuid,
    mock_get_orgs_and_services_associated_with_branding_no_orgs,
):
    client_request.login(platform_admin_user)

    page = client_request.get(".platform_admin_confirm_archive_email_branding", branding_id=fake_uuid)

    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "This email branding is in use. You cannot delete it."
    )


def test_platform_admin_archive_email_branding(
    client_request,
    platform_admin_user,
    mocker,
    fake_uuid,
    mock_get_email_branding,
):
    mock_archive = mocker.patch("app.email_branding_client.archive_email_branding")

    client_request.login(platform_admin_user)

    client_request.post(
        ".platform_admin_archive_email_branding",
        branding_id=fake_uuid,
        _expected_redirect=url_for(".email_branding"),
    )
    mock_archive.assert_called_once_with(branding_id=fake_uuid)


def test_temp_logo_is_shown_after_uploading_logo(
    client_request,
    platform_admin_user,
    mocker,
):
    mocker.patch("app.main.views.email_branding.logo_client.save_temporary_logo", return_value="email/test.png")
    mocker.patch("app.extensions.antivirus_client.scan", return_value=True)

    client_request.login(platform_admin_user)
    page = client_request.post(
        "main.platform_admin_create_email_branding",
        _data={"file": (BytesIO(b""), "test.png")},
        _content_type="multipart/form-data",
        _follow_redirects=True,
    )

    assert page.select_one("#logo-img > img").attrs["src"].endswith("email/test.png")


def test_logo_persisted_when_organisation_saved(
    client_request, platform_admin_user, mock_create_email_branding, mocker
):
    mock_save_temporary = mocker.patch("app.main.views.email_branding.logo_client.save_temporary_logo")
    mock_save_permanent = mocker.patch("app.main.views.email_branding.logo_client.save_permanent_logo")

    client_request.login(platform_admin_user)
    client_request.post(
        "main.platform_admin_create_email_branding",
        logo_key="test.png",
        _content_type="multipart/form-data",
    )

    assert not mock_save_temporary.called
    assert mock_save_permanent.called
    assert mock_create_email_branding.called


@pytest.mark.parametrize(
    "colour_hex, expected_status_code",
    [
        ("#FF00FF", 302),
        ("hello", 400),
        ("", 302),
    ],
)
def test_colour_regex_validation(
    client_request, platform_admin_user, colour_hex, expected_status_code, mock_create_email_branding
):
    data = {"logo": None, "colour": colour_hex, "text": "new text", "name": "new name", "brand_type": "org"}

    client_request.login(platform_admin_user)
    client_request.post(
        "main.platform_admin_create_email_branding",
        _content_type="multipart/form-data",
        _data=data,
        _expected_status=expected_status_code,
    )


def test_create_email_branding_government_identity_logo_form(client_request, platform_admin_user):
    client_request.login(platform_admin_user)
    page = client_request.get(
        ".create_email_branding_government_identity_logo",
    )
    inputs = page.select("input[type=radio][name=coat_of_arms_or_insignia]")
    values = [input["value"] for input in inputs]
    images = [page.select_one("label[for=" + input["id"] + "] img")["src"] for input in inputs]

    assert list(zip(values, images, strict=True)) == [
        (
            "Department for Business & Trade",
            "https://static.example.com/images/branding/insignia/"
            "Department for Business & Trade.png?ec972edf4b61fe0a0064da65b0e2564b",
        ),
        (
            "Foreign, Commonwealth & Development Office",
            "https://static.example.com/images/branding/insignia/"
            "Foreign, Commonwealth & Development Office.png?5f774527e45c4f03ca4a1167acdc0826",
        ),
        (
            "HM Coastguard",
            "https://static.example.com/images/branding/insignia/HM Coastguard.png?75bec666533897525a3545570d04e3d4",
        ),
        (
            "HM Government",
            "https://static.example.com/images/branding/insignia/HM Government.png?9e4dcaacf920fab30add8dcb87bda726",
        ),
        (
            "HM Revenue & Customs",
            "https://static.example.com/images/branding/insignia/"
            "HM Revenue & Customs.png?6378474ceb33424b4e508a32ca4b6315",
        ),
        (
            "Home Office",
            "https://static.example.com/images/branding/insignia/Home Office.png?cc928b18d70992c0b85e01c6af30dcc2",
        ),
        (
            "Ministry of Defence",
            "https://static.example.com/images/branding/insignia/"
            "Ministry of Defence.png?e58dccf7441c42356c5947a191a732ed",
        ),
        (
            "Scotland Office",
            "https://static.example.com/images/branding/insignia/Scotland Office.png?9da8a4c042f1b0f0631bb4ff98330dde",
        ),
        (
            "Wales Office",
            "https://static.example.com/images/branding/insignia/Wales Office.png?82e7cde43c4448c6f0ddaa481fa7bb2a",
        ),
    ]

    for input in inputs:
        assert normalize_spaces(page.select_one("label[for=" + input["id"] + "]").text) == input["value"]


def test_post_create_email_branding_government_identity_logo_form(client_request, platform_admin_user):
    client_request.login(platform_admin_user)
    client_request.post(
        ".create_email_branding_government_identity_logo",
        text="Department of Social Affairs and Citizenship",
        _data={
            "coat_of_arms_or_insignia": "HM Government",
        },
        _expected_redirect=url_for(
            ".create_email_branding_government_identity_colour",
            filename="HM Government",
            text="Department of Social Affairs and Citizenship",
        ),
    )


def test_create_email_branding_government_identity_colour(client_request, platform_admin_user):
    client_request.login(platform_admin_user)
    page = client_request.get(
        ".create_email_branding_government_identity_colour",
        filename="HM Government",
    )
    inputs = page.select("input[type=radio][name=colour]")
    labels = [normalize_spaces(page.select_one("label[for=" + input["id"] + "]").text) for input in inputs]
    values = [input["value"] for input in inputs]

    assert list(zip(labels, values, strict=True)) == [
        ("Attorney General’s Office", "#9f1888"),
        ("Cabinet Office", "#005abb"),
        ("Civil Service", "#af292e"),
        ("Department for Business & Trade", "#cf102d"),
        ("Department for Business Innovation & Skills", "#003479"),
        ("Department for Digital, Culture, Media & Sport", "#d40072"),
        ("Department for Education", "#003a69"),
        ("Department for Environment Food & Rural Affairs", "#00a33b"),
        ("Department for International Development", "#002878"),
        ("Department for Levelling Up, Housing & Communities", "#012169"),
        ("Department for Transport", "#006c56"),
        ("Department for Work & Pensions", "#00beb7"),
        ("Department of Health & Social Care", "#00ad93"),
        ("Foreign, Commonwealth & Development Office", "#012169"),
        ("Government Equalities Office", "#9325b2"),
        ("HM Government", "#0076c0"),
        ("HM Revenue & Customs", "#009390"),
        ("HM Treasury", "#af292e"),
        ("Home Office", "#9325b2"),
        ("Ministry of Defence", "#4d2942"),
        ("Ministry of Justice", "#231f20"),
        ("Northern Ireland Office", "#002663"),
        ("Office of the Advocate General for Scotland", "#002663"),
        ("Office of the Leader of the House of Commons", "#317023"),
        ("Office of the Leader of the House of Lords", "#9c132e"),
        ("Scotland Office", "#002663"),
        ("UK Export Finance", "#005747"),
        ("Wales Office", "#a33038"),
    ]

    for input in inputs:
        assert page.select_one("label[for=" + input["id"] + "] .email-branding-coloured-stripe")["style"] == (
            "background: " + input["value"] + ";"
        )
        assert page.select_one("label[for=" + input["id"] + "] img")["src"] == (
            "https://static.example.com/images/branding/insignia/HM Government.png?9e4dcaacf920fab30add8dcb87bda726"
        )


@pytest.mark.parametrize(
    "extra_args",
    (
        {},
        {"filename": "foo"},
        {"filename": "foo.png"},
    ),
)
def test_create_email_branding_government_identity_colour_400_if_no_filename_or_file_doesnt_exist(
    client_request,
    platform_admin_user,
    extra_args,
):
    client_request.login(platform_admin_user)
    client_request.get(
        ".create_email_branding_government_identity_colour", _expected_status=400, _test_page_title=False, **extra_args
    )


def test_post_create_email_branding_government_identity_form_colour(
    client_request,
    platform_admin_user,
    mocker,
):
    mock_save_temporary = mocker.patch(
        "app.main.views.email_branding.logo_client.save_temporary_logo",
        return_value="temporary/email/example.png",
    )
    client_request.login(platform_admin_user)

    client_request.post(
        ".create_email_branding_government_identity_colour",
        filename="HM Government",
        text="Department of Social Affairs and Citizenship",
        _data={
            "colour": "#005abb",
        },
        _expected_redirect=url_for(
            "main.platform_admin_create_email_branding",
            logo_key="temporary/email/example.png",
            colour="#005abb",
            name="Department of Social Affairs and Citizenship",
            text="Department of Social Affairs and Citizenship",
            back="government-identity",
            government_identity="HM Government",
        ),
    )

    assert mock_save_temporary.call_args_list == [mocker.call(mocker.ANY, logo_type="email")]
    logo_bytes_io = mock_save_temporary.call_args_list[0][0][0]
    assert logo_bytes_io.read() == (get_insignia_asset_path() / "HM Government.png").resolve().read_bytes()
