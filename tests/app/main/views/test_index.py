from functools import partial

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from freezegun import freeze_time

from app.main.forms import FieldWithNoneOption
from tests.conftest import SERVICE_ONE_ID, normalize_spaces, sample_uuid


def test_non_logged_in_user_can_see_homepage(
    client_request,
    mock_get_service_and_organisation_counts,
):
    client_request.logout()
    page = client_request.get("main.index", _test_page_title=False)

    assert page.select_one("h1").text.strip() == "Send emails, text messages and letters to your users"

    assert page.select_one("a[role=button][draggable=false]")["href"] == url_for("main.register")

    assert page.select_one("meta[name=description]")["content"].strip() == (
        "GOV.UK Notify lets you send emails, text messages and letters "
        "to your users. Try it now if you work in central government, a "
        "local authority, or the NHS."
    )

    assert normalize_spaces(page.select_one("#whos-using-notify").text) == (
        "Who’s using GOV.UK Notify "
        "There are 111 organisations and 9,999 services using Notify. "
        "See the list of services and organisations."
    )
    assert page.select_one("#whos-using-notify a")["href"] == url_for("main.performance")


def test_logged_in_user_redirects_to_choose_account(
    client_request,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_login,
):
    client_request.get(
        "main.index",
        _expected_status=302,
    )
    client_request.get(
        "main.sign_in", _expected_status=302, _expected_redirect=url_for("main.show_accounts_or_dashboard")
    )


def test_robots(client_request):
    client_request.get_url("/robots.txt", _expected_status=404)


@pytest.mark.parametrize(
    "endpoint, kwargs",
    (
        ("sign_in", {}),
        ("support", {}),
        ("support_public", {}),
        ("triage", {}),
        ("feedback", {"ticket_type": "ask-question-give-feedback"}),
        ("feedback", {"ticket_type": "general"}),
        ("feedback", {"ticket_type": "report-problem"}),
        ("bat_phone", {}),
        ("thanks", {}),
        ("register", {}),
        pytest.param("index", {}, marks=pytest.mark.xfail(raises=AssertionError)),
    ),
)
@freeze_time("2012-12-12 12:12")  # So we don’t go out of business hours
def test_hiding_pages_from_search_engines(
    client_request,
    mock_get_service_and_organisation_counts,
    endpoint,
    kwargs,
):
    client_request.logout()
    response = client_request.get_response(f"main.{endpoint}", **kwargs)
    assert "X-Robots-Tag" in response.headers
    assert response.headers["X-Robots-Tag"] == "noindex"

    page = BeautifulSoup(response.data.decode("utf-8"), "html.parser")
    assert page.select_one("meta[name=robots]")["content"] == "noindex"


@pytest.mark.parametrize(
    "view",
    [
        "cookies",
        "guidance_api_documentation",
        "guidance_billing_details",
        "guidance_delivery_times",
        "guidance_email_branding",
        "guidance_features",
        "guidance_formatting",
        "guidance_how_to_pay",
        "guidance_letter_branding",
        "guidance_pricing_letters",
        "guidance_pricing_text_messages",
        "guidance_pricing",
        "guidance_receive_text_messages",
        "guidance_reply_to_email_address",
        "guidance_roadmap",
        "guidance_schedule_messages",
        "guidance_security",
        "guidance_send_files_by_email",
        "guidance_templates",
        "guidance_text_message_sender",
        "guidance_upload_a_letter",
        "guidance_using_notify",
        "guidance_who_can_use_notify",
        "privacy",
        "terms_of_use",
    ],
)
def test_static_pages(
    client_request,
    mock_get_organisation_by_domain,
    view,
):
    request = partial(client_request.get, "main.{}".format(view))

    # Check the page loads when user is signed in
    page = request()
    assert not page.select_one("meta[name=description]")

    # Check it still works when they don’t have a recent service
    with client_request.session_transaction() as session:
        session["service_id"] = None
    request()

    # Check it still works when they sign out
    client_request.logout()
    with client_request.session_transaction() as session:
        session["service_id"] = None
        session["user_id"] = None
    request()


def test_guidance_pages_link_to_service_pages_when_signed_in(
    client_request,
):
    request = partial(client_request.get, "main.guidance_formatting")
    selector = ".govuk-list--number li a"

    # Check the page loads when user is signed in
    page = request()
    assert page.select_one(selector)["href"] == url_for(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )

    # Check it still works when they don’t have a recent service
    with client_request.session_transaction() as session:
        session["service_id"] = None
    page = request()
    assert not page.select_one(selector)

    # Check it still works when they sign out
    client_request.logout()
    with client_request.session_transaction() as session:
        session["service_id"] = None
        session["user_id"] = None
    page = request()
    assert not page.select_one(selector)


@pytest.mark.parametrize(
    "old_url, expected_endpoint, expected_endpoint_kwargs",
    [
        ("/callbacks", "main.guidance_api_documentation", {}),
        ("/delivery-and-failure", "main.guidance_message_status", {}),
        ("/features/terms", "main.terms_of_use", {}),
        ("/features/using-notify", "main.guidance_using_notify", {}),
        ("/guidance_using_notify", "main.guidance_using_notify", {}),
        ("/information-risk-management", "main.guidance_security", {}),
        ("/information-security", "main.guidance_security", {}),
        ("/integration_testing", "main.guidance_api_documentation", {}),
        ("/integration-testing", "main.guidance_api_documentation", {}),
        ("/roadmap", "main.guidance_roadmap", {}),
        ("/terms", "main.terms_of_use", {}),
        ("/using-notify/guidance/message-status", "main.guidance_message_status", {}),
        ("/using-notify/guidance/message-status/sms", "main.guidance_message_status", {"notification_type": "sms"}),
        ("/using-notify/who-its-for", "main.guidance_who_can_use_notify", {}),
    ],
    ids=(lambda arg: arg if isinstance(arg, str) and arg.startswith("/") else ""),
)
def test_redirect_blueprint(client_request, old_url, expected_endpoint, expected_endpoint_kwargs):
    client_request.logout()
    client_request.get_url(
        old_url,
        _expected_status=301,
        _expected_redirect=url_for(expected_endpoint, **expected_endpoint_kwargs),
    )


def test_message_status_page_redirects_without_notification_type_specified(client_request):
    client_request.get(
        "main.guidance_message_status",
        _expected_redirect=url_for(
            "main.guidance_message_status",
            notification_type="email",
        ),
    )


def test_message_status_page_contains_link_to_support(client_request):
    page = client_request.get("main.guidance_message_status", notification_type="sms")
    sms_status_table = page.select_one("tbody")

    temp_fail_details_cell = sms_status_table.select_one("tr:nth-child(4) > td:nth-child(2)")
    assert temp_fail_details_cell.select_one("a")["href"] == url_for("main.support")


def test_terms_page_has_correct_content(client_request):
    terms_page = client_request.get("main.terms_of_use")
    assert normalize_spaces(terms_page.select("main p")[0].text) == (
        "These terms apply to your service’s use of GOV.UK Notify. You must be the service manager to accept them."
    )


def test_css_is_served_from_correct_path(client_request):

    page = client_request.get("main.guidance_api_documentation")  # easy static page

    for index, link in enumerate(page.select("link[rel=stylesheet]")):
        assert link["href"].startswith(
            [
                "https://static.example.com/stylesheets/main.css?",
                "https://static.example.com/stylesheets/print.css?",
            ][index]
        )


def test_resources_that_use_asset_path_variable_have_correct_path(client_request):

    page = client_request.get("main.guidance_api_documentation")  # easy static page

    favicon = page.select_one('link[type="image/x-icon"]')

    assert favicon.attrs["href"].startswith("https://static.example.com/images/favicon.ico")


@pytest.mark.parametrize(
    "extra_args, email_branding_retrieved",
    (
        (
            {},
            False,
        ),
        (
            {"branding_style": "__NONE__"},
            False,
        ),
        (
            {"branding_style": "custom", "type": "org"},
            False,
        ),
        (
            {"branding_style": sample_uuid()},
            True,
        ),
    ),
)
def test_email_branding_preview(
    client_request,
    mock_get_email_branding,
    extra_args,
    email_branding_retrieved,
):
    page = client_request.get("main.email_template", _test_page_title=False, **extra_args)
    assert page.select_one("title").text == "Email branding preview"
    assert mock_get_email_branding.called is email_branding_retrieved


@pytest.mark.parametrize("filename", [None, FieldWithNoneOption.NONE_OPTION_VALUE])
@pytest.mark.parametrize("branding_style", [None, FieldWithNoneOption.NONE_OPTION_VALUE])
def test_letter_template_preview_handles_no_branding_style_or_filename_correctly(
    client_request,
    branding_style,
    filename,
):
    page = client_request.get(
        "main.letter_template",
        _test_page_title=False,
        # Letter HTML doesn’t use the Design System, so elements won’t have class attributes
        _test_for_elements_without_class=False,
        branding_style=branding_style,
        filename=filename,
    )

    image_link = page.select_one("img")["src"]

    assert image_link == url_for("no_cookie.letter_branding_preview_image", filename="no-branding", page=1)


@pytest.mark.parametrize("filename", [None, FieldWithNoneOption.NONE_OPTION_VALUE])
def test_letter_template_preview_links_to_the_correct_image_when_passed_existing_branding(
    client_request,
    mock_get_letter_branding_by_id,
    filename,
):
    page = client_request.get(
        "main.letter_template",
        _test_page_title=False,
        # Letter HTML doesn’t use the Design System, so elements won’t have class attributes
        _test_for_elements_without_class=False,
        branding_style="12341234-1234-1234-1234-123412341234",
        filename=filename,
    )

    mock_get_letter_branding_by_id.assert_called_once_with("12341234-1234-1234-1234-123412341234")

    image_link = page.select_one("img")["src"]

    assert image_link == url_for("no_cookie.letter_branding_preview_image", filename="hm-government", page=1)


@pytest.mark.parametrize("branding_style", [None, FieldWithNoneOption.NONE_OPTION_VALUE])
def test_letter_template_preview_links_to_the_correct_image_when_passed_a_filename(
    client_request,
    branding_style,
):
    page = client_request.get(
        "main.letter_template",
        _test_page_title=False,
        # Letter HTML doesn’t use the Design System, so elements won’t have class attributes
        _test_for_elements_without_class=False,
        branding_style=branding_style,
        filename="foo.svg",
    )

    image_link = page.select_one("img")["src"]

    assert image_link == url_for("no_cookie.letter_branding_preview_image", filename="foo.svg", page=1)


def test_letter_template_preview_returns_400_if_both_branding_style_and_filename_provided(
    client_request,
):
    client_request.get(
        "main.letter_template",
        branding_style="some-branding",
        filename="some-filename",
        _test_page_title=False,
        _expected_status=400,
    )


def test_letter_template_preview_headers(
    client_request,
    mock_get_letter_branding_by_id,
):
    response = client_request.get_response("main.letter_template")

    assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"


def test_letter_spec_redirect(client_request):
    client_request.get(
        "main.letter_spec",
        _expected_status=302,
        _expected_redirect=(
            "https://docs.notifications.service.gov.uk" "/documentation/images/notify-pdf-letter-spec-v2.4.pdf"
        ),
    )


def test_letter_spec_redirect_with_non_logged_in_user(client_request):
    client_request.logout()
    client_request.get(
        "main.letter_spec",
        _expected_status=302,
        _expected_redirect=(
            "https://docs.notifications.service.gov.uk" "/documentation/images/notify-pdf-letter-spec-v2.4.pdf"
        ),
    )


def test_font_preload(
    client_request,
    mock_get_service_and_organisation_counts,
):
    client_request.logout()
    page = client_request.get("main.index", _test_page_title=False)

    preload_tags = page.select('link[rel=preload][as=font][type="font/woff2"][crossorigin]')

    assert len(preload_tags) == 2, "Run `npm run build` to copy fonts into app/static/fonts/"

    for element in preload_tags:
        assert element["href"].startswith("https://static.example.com/fonts/")
        assert element["href"].endswith(".woff2")


def test_sms_price(
    client_request,
    mock_get_service_and_organisation_counts,
):
    client_request.logout()

    home_page = client_request.get("main.index", _test_page_title=False)
    text_message_pricing_page = client_request.get("main.guidance_pricing_text_messages")

    expected_rate = "1.97"
    assert (
        normalize_spaces(home_page.select(".product-page-section")[5].select(".govuk-grid-column-one-half")[1].text)
        == f"Text messages Up to 40,000 free text messages a year, then {expected_rate} pence per message"
    )

    assert (
        f"When a service has used its annual allowance, it costs "
        f"{expected_rate} pence (plus VAT) for each text message you "
        f"send."
    ) in normalize_spaces(text_message_pricing_page.text)


def test_bulk_sending_limits(client_request):
    page = client_request.get("main.guidance_bulk_sending")
    paragraphs = page.select("main p")

    assert normalize_spaces(paragraphs[0].text) == (
        "You can send a batch of up to 100,000" " personalised messages at once."
    )
    assert normalize_spaces(paragraphs[1].text) == (
        "There’s a maximum daily limit of 250,000 emails, 250,000 text messages and 20,000 letters. "
        "If you need to discuss these limits, contact us."
    )


def test_trial_mode_sending_limits(client_request):
    page = client_request.get("main.guidance_trial_mode")

    assert [normalize_spaces(li.text) for li in page.select_one("main ul").select("li")] == [
        "send messages to yourself and other people in your team",
        "send 50 emails per day",
        "send 50 text messages per day",
        "create letter templates, but not send them",
    ]
