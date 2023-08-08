from io import BytesIO
from unittest.mock import Mock
from uuid import UUID

import pytest
from botocore.exceptions import ClientError as BotoClientError
from flask import url_for
from notifications_python_client.errors import HTTPError

from tests.conftest import create_letter_branding, normalize_spaces


def test_letter_branding_page_shows_full_branding_list(
    client_request, platform_admin_user, mock_get_all_letter_branding
):
    client_request.login(platform_admin_user)
    page = client_request.get(".letter_branding")

    links = page.select(".browse-list-item a")
    brand_names = [normalize_spaces(link.text) for link in links]
    hrefs = [link["href"] for link in links]

    assert normalize_spaces(page.select_one("h1").text) == "Letter branding"

    assert page.select(".govuk-grid-column-three-quarters a")[-1]["href"] == url_for("main.create_letter_branding")

    assert brand_names == [
        "HM Government",
        "Land Registry",
        "Animal and Plant Health Agency",
    ]

    assert hrefs == [
        url_for(".platform_admin_view_letter_branding", branding_id=str(UUID(int=0))),
        url_for(".platform_admin_view_letter_branding", branding_id=str(UUID(int=1))),
        url_for(".platform_admin_view_letter_branding", branding_id=str(UUID(int=2))),
    ]


@pytest.mark.parametrize(
    "user_fixture, expected_response_status", (("api_user_active_email_auth", 403), ("platform_admin_user", 200))
)
def test_view_letter_branding_requires_platform_admin(
    mocker, client_request, mock_get_letter_branding_by_id, user_fixture, expected_response_status, request, fake_uuid
):
    mocker.patch(
        "app.letter_branding_client.get_orgs_and_services_associated_with_branding",
    )
    user = request.getfixturevalue(user_fixture)
    client_request.login(user)
    page = client_request.get(
        ".platform_admin_view_letter_branding", branding_id=fake_uuid, _expected_status=expected_response_status
    )

    if expected_response_status == 200:
        preview = page.select_one("iframe")
        assert preview["src"] == "/_letter?branding_style=6ce466d0-fd6a-11e5-82f5-e0accb9d11a6"


def test_view_letter_branding_with_services_but_no_orgs(
    mocker,
    client_request,
    platform_admin_user,
    mock_get_letter_branding_by_id,
    fake_uuid,
):
    mocker.patch(
        "app.letter_branding_client.get_orgs_and_services_associated_with_branding",
        side_effect=lambda letter_branding_id: {
            "data": {
                "services": [{"name": "service 1", "id": "1234"}, {"name": "service 2", "id": "5678"}],
                "organisations": [],
            }
        },
    )

    client_request.login(platform_admin_user)

    page = client_request.get(".platform_admin_view_letter_branding", branding_id=fake_uuid)

    assert page.select_one(".hint").text.strip() == "No organisations use this branding as their default."

    list_of_service_links = page.select(".browse-list-item")

    link_1 = list_of_service_links[0].select_one("a")
    assert link_1.text.strip() == "service 1"
    assert link_1["href"] == url_for(".service_settings", service_id="1234")

    link_2 = list_of_service_links[1].select_one("a")
    assert link_2.text.strip() == "service 2"
    assert link_2["href"] == url_for(".service_settings", service_id="5678")


def test_view_letter_branding_with_org_but_no_services(
    mocker,
    client_request,
    platform_admin_user,
    mock_get_letter_branding_by_id,
    fake_uuid,
):
    mocker.patch(
        "app.letter_branding_client.get_orgs_and_services_associated_with_branding",
        side_effect=lambda letter_branding_id: {
            "data": {"services": [], "organisations": [{"name": "organisation 1", "id": "1234"}]}
        },
    )

    client_request.login(platform_admin_user)

    page = client_request.get(".platform_admin_view_letter_branding", branding_id=fake_uuid)

    assert page.select_one(".hint").text.strip() == "No services use this branding."

    list_of_organisation_links = page.select(".browse-list-item")

    link_1 = list_of_organisation_links[0].select_one("a")
    assert link_1.text.strip() == "organisation 1"
    assert link_1["href"] == url_for(".organisation_settings", org_id="1234")


@pytest.mark.parametrize(
    "created_at, updated_at", [("2022-12-06T09:59:56.000000Z", "2023-01-20T11:59:56.000000Z"), (None, None)]
)
def test_view_letter_branding_shows_created_by_and_helpful_dates_if_available(
    client_request,
    platform_admin_user,
    fake_uuid,
    mocker,
    created_at,
    updated_at,
):
    mocker.patch(
        "app.letter_branding_client.get_orgs_and_services_associated_with_branding",
        side_effect=lambda letter_branding_id: {"data": {"services": [], "organisations": []}},
    )
    client_request.login(platform_admin_user)

    def _get_letter_branding(id):
        return create_letter_branding(
            id,
            non_standard_values={
                "created_by": "1234-5678-abcd-efgh",
                "created_at": created_at,
                "updated_at": updated_at,
            },
        )["letter_branding"]

    mocker.patch("app.models.branding.letter_branding_client.get_letter_branding", side_effect=_get_letter_branding)

    user = {"id": "1234-5678-abcd-efgh", "name": "Arwa Suren"}
    mocker.patch("app.models.branding.user_api_client.get_user", return_value=user)

    page = client_request.get(".platform_admin_view_letter_branding", branding_id=fake_uuid)

    created_by_link = page.select("main p > a")[0]
    assert created_by_link.text.strip() == user["name"]
    assert created_by_link["href"] == url_for(".user_information", user_id=user["id"])

    if created_at:
        assert "on Tuesday 06 December 2022" in page.select("p")[-2].text

    if updated_at:
        assert "on Friday 20 January 2023" in page.select("p")[-1].text


def test_view_letter_branding_bottom_links(
    mocker,
    client_request,
    platform_admin_user,
    mock_get_letter_branding_by_id,
    fake_uuid,
):
    mocker.patch(
        "app.letter_branding_client.get_orgs_and_services_associated_with_branding",
        side_effect=lambda letter_branding_id: {"data": {"services": [], "organisations": []}},
    )
    client_request.login(platform_admin_user)

    page = client_request.get(".platform_admin_view_letter_branding", branding_id=fake_uuid)

    bottom_links = page.select(".page-footer-link")

    edit_link = bottom_links[0].select_one("a")
    assert edit_link.text.strip() == "Edit this branding"
    assert edit_link["href"] == url_for(".update_letter_branding", branding_id=fake_uuid)


def test_update_letter_branding_shows_the_current_letter_brand(
    client_request,
    platform_admin_user,
    mock_get_letter_branding_by_id,
    fake_uuid,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        ".update_letter_branding",
        branding_id=fake_uuid,
    )

    assert page.select_one("h1").text == "Update letter branding"
    assert page.select_one("#logo-img > img")["src"].endswith("/hm-government.svg")
    assert page.select_one("#name").attrs.get("value") == "HM Government"
    assert page.select_one("#file").attrs.get("accept") == ".svg"


def test_update_letter_branding_with_new_valid_file_shows_page_with_file_preview(
    mocker, client_request, platform_admin_user, mock_get_letter_branding_by_id, fake_uuid
):
    mock_save_temporary = mocker.patch(
        "app.main.views.letter_branding.logo_client.save_temporary_logo", return_value="temporary.svg"
    )
    mocker.patch("app.extensions.antivirus_client.scan", return_value=True)

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".update_letter_branding",
        branding_id=fake_uuid,
        _data={"file": (BytesIO("".encode("utf-8")), "logo.svg")},
        _follow_redirects=True,
    )

    assert page.select_one("#logo-img > img")["src"].endswith("temporary.svg")
    assert page.select_one("#name").attrs.get("value") == "HM Government"

    assert mock_save_temporary.call_args_list == [mocker.call(mocker.ANY, logo_type="letter")]


def test_update_letter_branding_when_uploading_invalid_file(
    client_request,
    platform_admin_user,
    mock_get_letter_branding_by_id,
    fake_uuid,
    mocker,
):
    mocker.patch("app.extensions.antivirus_client.scan", return_value=True)

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".update_letter_branding",
        branding_id=fake_uuid,
        _data={"file": (BytesIO("".encode("utf-8")), "test.png")},
        _follow_redirects=True,
    )

    assert page.select_one("h1").text == "Update letter branding"
    assert page.select_one(".error-message").text.strip() == "SVG Images only!"


def test_update_letter_branding_with_original_file_and_new_details(
    mocker, client_request, platform_admin_user, mock_get_all_letter_branding, mock_get_letter_branding_by_id, fake_uuid
):
    mock_client_update = mocker.patch("app.main.views.letter_branding.letter_branding_client.update_letter_branding")
    mock_save_temporary = mocker.patch("app.main.views.letter_branding.logo_client.save_temporary_logo")
    mock_save_permanent = mocker.patch("app.main.views.letter_branding.logo_client.save_permanent_logo")
    mock_create_update_letter_branding_event = mocker.patch(
        "app.main.views.letter_branding.create_update_letter_branding_event"
    )

    client_request.login(platform_admin_user)
    client_request.post(
        ".update_letter_branding",
        branding_id=fake_uuid,
        _data={"name": "Updated name", "operation": "branding-details"},
        _follow_redirects=False,
        _expected_redirect=url_for(".platform_admin_view_letter_branding", branding_id=fake_uuid),
    )

    assert mock_save_temporary.called is False
    assert mock_save_permanent.called is False

    mock_client_update.assert_called_once_with(
        branding_id=fake_uuid,
        filename="hm-government",
        name="Updated name",
        updated_by_id=fake_uuid,
    )
    mock_create_update_letter_branding_event.assert_called_once_with(
        letter_branding_id=fake_uuid,
        updated_by_id=fake_uuid,
        old_letter_branding={"id": fake_uuid, "name": "HM Government", "filename": "hm-government"},
    )


def test_update_letter_branding_shows_form_errors_on_name_fields(
    mocker, client_request, platform_admin_user, mock_get_letter_branding_by_id, fake_uuid, logo_client
):
    mocker.patch("app.main.views.letter_branding.letter_branding_client.update_letter_branding")

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".update_letter_branding",
        branding_id=fake_uuid,
        logo=logo_client.get_logo_key("hm-government.svg", logo_type="letter"),
        _data={"name": "", "operation": "branding-details"},
        _follow_redirects=True,
    )

    error_messages = page.select(".govuk-error-message")

    assert page.select_one("h1").text == "Update letter branding"
    assert len(error_messages) == 1
    assert "Error: Enter a name for the branding" in error_messages[0].text.strip()


def test_update_letter_branding_shows_database_errors_on_name_field(
    mocker,
    client_request,
    platform_admin_user,
    mock_get_letter_branding_by_id,
    fake_uuid,
):
    mocker.patch(
        "app.main.views.letter_branding.letter_branding_client.update_letter_branding",
        side_effect=HTTPError(
            response=Mock(status_code=400, json={"result": "error", "message": {"name": {"name already in use"}}}),
            message={"name": ["name already in use"]},
        ),
    )

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".update_letter_branding",
        branding_id=fake_uuid,
        _data={"name": "my brand", "operation": "branding-details"},
        _expected_status=200,
    )

    error_message = page.select_one(".govuk-error-message").text.strip()

    assert page.select_one("h1").text == "Update letter branding"
    assert "name already in use" in error_message


def test_update_letter_branding_with_new_file_and_new_details(
    mocker, client_request, platform_admin_user, mock_get_all_letter_branding, mock_get_letter_branding_by_id, fake_uuid
):
    mock_save_temporary = mocker.patch("app.main.views.letter_branding.logo_client.save_temporary_logo")
    mock_save_permanent = mocker.patch(
        "app.main.views.letter_branding.logo_client.save_permanent_logo", return_value="permanent.svg"
    )
    mock_client_update = mocker.patch("app.main.views.letter_branding.letter_branding_client.update_letter_branding")
    mock_create_update_letter_branding_event = mocker.patch(
        "app.main.views.letter_branding.create_update_letter_branding_event"
    )

    branding_id = str(UUID(int=0))

    client_request.login(platform_admin_user)
    client_request.post(
        ".update_letter_branding",
        branding_id=branding_id,
        logo="temporary-logo.svg",
        _data={"name": "Updated name", "operation": "branding-details"},
        _follow_redirects=False,
        _expected_redirect=url_for(".platform_admin_view_letter_branding", branding_id=branding_id),
    )

    mock_client_update.assert_called_once_with(
        branding_id=branding_id, filename="permanent", name="Updated name", updated_by_id=fake_uuid
    )
    assert mock_save_temporary.called is False
    assert mock_save_permanent.call_args_list == [
        mocker.call("temporary-logo.svg", logo_type="letter", logo_key_extra="Updated name")
    ]
    mock_create_update_letter_branding_event.assert_called_once_with(
        letter_branding_id=branding_id,
        updated_by_id=fake_uuid,
        old_letter_branding={"id": branding_id, "name": "HM Government", "filename": "hm-government"},
    )


def test_update_letter_branding_does_not_save_to_db_if_uploading_fails(
    mocker,
    client_request,
    platform_admin_user,
    mock_get_letter_branding_by_id,
    fake_uuid,
    logo_client,
):
    mock_client_update = mocker.patch("app.main.views.letter_branding.letter_branding_client.update_letter_branding")
    mock_create_update_letter_branding_event = mocker.patch(
        "app.main.views.letter_branding.create_update_letter_branding_event"
    )
    mocker.patch(
        "app.main.views.letter_branding.logo_client.save_permanent_logo", side_effect=BotoClientError({}, "error")
    )

    logo_path = logo_client.get_logo_key("logo.svg", logo_type="letter")

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".update_letter_branding",
        branding_id=fake_uuid,
        logo=logo_path,
        _data={"name": "Updated name", "operation": "branding-details"},
        _expected_status=200,
    )
    assert page.select_one("h1").text == "Update letter branding"
    assert page.select_one(".error-message").text.strip() == "Error saving uploaded file - try uploading again"
    assert not mock_client_update.called
    assert not mock_create_update_letter_branding_event.called


def test_create_letter_branding_does_not_show_branding_info(
    client_request,
    platform_admin_user,
):
    client_request.login(platform_admin_user)
    page = client_request.get(".create_letter_branding")

    assert page.select_one("#logo-img > img") is None
    assert page.select_one("#name").attrs.get("value") is None
    assert page.select_one("#file").attrs.get("accept") == ".svg"


def test_create_letter_branding_when_uploading_valid_file(mocker, client_request, platform_admin_user, fake_uuid):
    mock_save_temporary = mocker.patch(
        "app.main.views.letter_branding.logo_client.save_temporary_logo", return_value="temporary.svg"
    )
    mocker.patch("app.extensions.antivirus_client.scan", return_value=True)

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".create_letter_branding",
        _data={
            "file": (
                BytesIO(
                    """
            <svg height="100" width="100">
            <circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" /></svg>
        """.encode(
                        "utf-8"
                    )
                ),
                "logo.svg",
            )
        },
        _follow_redirects=True,
    )

    assert page.select_one("#logo-img > img").attrs["src"].endswith("temporary.svg")
    assert mock_save_temporary.call_args_list == [mocker.call(mocker.ANY, logo_type="letter")]


@pytest.mark.parametrize(
    "scan_result, expected_status_code",
    (
        (True, 302),
        (False, 200),
    ),
)
def test_create_letter_branding_calls_antivirus_scan(
    mocker, client_request, platform_admin_user, fake_uuid, scan_result, expected_status_code
):
    mock_antivirus = mocker.patch("app.extensions.antivirus_client.scan", return_value=scan_result)
    mock_save_temporary = mocker.patch(
        "app.main.views.letter_branding.logo_client.save_temporary_logo", return_value="temporary.svg"
    )

    client_request.login(platform_admin_user)
    client_request.post(
        ".create_letter_branding",
        _data={
            "file": (
                BytesIO(
                    """
            <svg height="100" width="100">
            <circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" /></svg>
        """.encode(
                        "utf-8"
                    )
                ),
                "logo.svg",
            )
        },
        _expected_status=expected_status_code,
    )

    assert mock_antivirus.call_count == 1
    assert mock_save_temporary.call_count == (1 if scan_result else 0)


@pytest.mark.parametrize(
    "svg_contents, expected_error",
    (
        (
            """
            <svg height="100" width="100">
            <image href="someurlgoeshere" x="0" y="0" height="100" width="100"></image></svg>
        """,
            "This SVG has an embedded raster image in it and will not render well",
        ),
        (
            """
            <svg height="100" width="100">
                <text>Will render differently depending on fonts installed</text>
            </svg>
        """,
            "This SVG has text which has not been converted to paths and may not render well",
        ),
    ),
)
def test_create_letter_branding_fails_validation_when_uploading_SVG_with_bad_element(
    mocker,
    client_request,
    platform_admin_user,
    svg_contents,
    expected_error,
):
    mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    mock_save_temporary = mocker.patch("app.main.views.letter_branding.logo_client.save_temporary_logo")

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".create_letter_branding",
        _data={"file": (BytesIO(svg_contents.encode("utf-8")), "test.svg")},
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Add letter branding"
    assert normalize_spaces(page.select_one(".error-message").text) == expected_error

    assert page.select("div#logo-img") == []

    assert mock_save_temporary.called is False


def test_create_letter_branding_when_uploading_invalid_file(
    client_request,
    platform_admin_user,
    mocker,
):
    mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    client_request.login(platform_admin_user)
    page = client_request.post(
        ".create_letter_branding",
        _data={"file": (BytesIO("".encode("utf-8")), "test.png")},
        _follow_redirects=True,
    )
    assert page.select_one("h1").text == "Add letter branding"
    assert page.select_one(".error-message").text.strip() == "SVG Images only!"


def test_create_new_letter_branding_shows_preview_of_logo(client_request, platform_admin_user, fake_uuid, logo_client):
    temp_logo = logo_client.get_logo_key("temp.svg", logo_type="letter")

    client_request.login(platform_admin_user)
    page = client_request.get(
        ".create_letter_branding",
        logo=temp_logo,
    )

    assert page.select_one("h1").text == "Add letter branding"
    assert page.select_one("#logo-img > img").attrs["src"].endswith(temp_logo)


def test_create_letter_branding_shows_an_error_when_submitting_details_with_no_logo(
    client_request, platform_admin_user
):
    client_request.login(platform_admin_user)
    page = client_request.post(
        ".create_letter_branding",
        _data={"name": "Test brand", "operation": "branding-details"},
        _expected_status=200,
    )

    assert page.select_one("h1").text == "Add letter branding"
    assert page.select_one(".error-message").text.strip() == "You need to upload a file to submit"


def test_create_letter_branding_persists_logo_when_all_data_is_valid(
    mocker,
    client_request,
    platform_admin_user,
    mock_get_all_letter_branding,
    fake_uuid,
    mock_create_letter_branding,
):
    mock_save_permanent = mocker.patch(
        "app.main.views.letter_branding.logo_client.save_permanent_logo", return_value="permanent.svg"
    )

    client_request.login(platform_admin_user)
    client_request.post(
        ".create_letter_branding",
        logo="temporary.svg",
        _data={"name": "Test brand", "operation": "branding-details"},
        _follow_redirects=False,
        _expected_redirect=url_for(".platform_admin_view_letter_branding", branding_id=fake_uuid),
    )

    mock_create_letter_branding.assert_called_once_with(
        filename="permanent", name="Test brand", created_by_id=fake_uuid
    )
    assert mock_save_permanent.call_args_list == [
        mocker.call("temporary.svg", logo_type="letter", logo_key_extra="Test brand")
    ]


def test_create_letter_branding_shows_form_errors_on_name_field(
    client_request, platform_admin_user, fake_uuid, logo_client
):
    temp_logo = logo_client.get_logo_key("test.svg", logo_type="letter")

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".create_letter_branding",
        logo=temp_logo,
        _data={"name": "", "operation": "branding-details"},
        _expected_status=200,
    )

    error_messages = page.select(".govuk-error-message")

    assert page.select_one("h1").text == "Add letter branding"
    assert len(error_messages) == 1
    assert "Error: Enter a name for the branding" in error_messages[0].text.strip()


def test_create_letter_branding_shows_database_errors_on_name_fields(
    mocker,
    client_request,
    platform_admin_user,
    fake_uuid,
):
    mocker.patch(
        "app.main.views.letter_branding.letter_branding_client.create_letter_branding",
        side_effect=HTTPError(
            response=Mock(status_code=400, json={"result": "error", "message": {"name": {"name already in use"}}}),
            message={"name": ["name already in use"]},
        ),
    )
    mock_save_permanent = mocker.patch("app.main.views.letter_branding.logo_client.save_permanent_logo")

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".create_letter_branding",
        logo="logo.svg",
        _data={"name": "my brand", "operation": "branding-details"},
        _expected_status=200,
    )

    error_message = page.select_one(".govuk-error-message").text.strip()

    assert page.select_one("h1").text == "Add letter branding"
    assert "name already in use" in error_message

    assert (
        mock_save_permanent.called is True
    ), "The logo should be persisted to S3 before the DB call so that we know it's there before creating the branding."
