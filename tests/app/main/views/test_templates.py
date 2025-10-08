import json
import uuid
from functools import partial
from io import BytesIO
from unittest.mock import ANY, Mock

import pytest
from flask import g, make_response, url_for
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError
from requests import RequestException

from app.main.forms import FieldWithNoneOption
from app.main.views_nl.templates import _save_letter_attachment
from app.models.service import Service
from tests import (
    NotifyBeautifulSoup,
    sample_uuid,
    template_json,
    template_version_json,
    validate_route_permission,
)
from tests.app.main.views.test_template_folders import (
    CHILD_FOLDER_ID,
    FOLDER_TWO_ID,
    PARENT_FOLDER_ID,
    _folder,
    _template,
)
from tests.conftest import (
    SERVICE_ONE_ID,
    SERVICE_TWO_ID,
    TEMPLATE_ONE_ID,
    ElementNotFound,
    create_active_caseworking_user,
    create_active_user_view_permissions,
    create_letter_contact_block,
    create_template,
    do_mock_get_page_counts_for_letter,
    normalize_spaces,
)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "permissions, expected_message",
    (
        (["email"], "You need a template before you can send emails, text messages or letters."),
        (["sms"], "You need a template before you can send emails, text messages or letters."),
        (["letter"], "You need a template before you can send emails, text messages or letters."),
        (["email", "sms", "letter"], "You need a template before you can send emails, text messages or letters."),
    ),
)
def test_should_show_empty_page_when_no_templates(
    client_request,
    service_one,
    mock_get_service_templates_when_no_templates_exist,
    mock_get_template_folders,
    mock_get_no_api_keys,
    permissions,
    expected_message,
):
    service_one["permissions"] = permissions

    page = client_request.get(
        "main.choose_template",
        service_id=service_one["id"],
    )

    assert normalize_spaces(page.select_one("h1").text) == "Templates"
    assert normalize_spaces(page.select_one("main p").text) == (expected_message)
    assert page.select_one("#add_new_folder_form")
    assert page.select_one("#add_new_template_form")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_add_template_form_if_service_has_folder_permission(
    client_request,
    service_one,
    mock_get_service_templates_when_no_templates_exist,
    mock_get_template_folders,
    mock_get_no_api_keys,
):
    page = client_request.get(
        "main.choose_template",
        service_id=service_one["id"],
    )

    assert normalize_spaces(page.select_one("h1").text) == "Templates"
    assert normalize_spaces(page.select_one("main p").text) == (
        "You need a template before you can send emails, text messages or letters."
    )
    assert [(item["name"], item["value"]) for item in page.select("[type=radio]")] == [
        ("add_template_by_template_type", "email"),
        ("add_template_by_template_type", "sms"),
    ]
    assert not page.select("main a")


@pytest.mark.parametrize(
    "user, expected_page_title, extra_args, expected_nav_links, expected_templates",
    [
        (
            create_active_user_view_permissions(),
            "Templates",
            {},
            ["Email", "Text message", "Letter"],
            [
                "sms_template_one",
                "sms_template_two",
                "email_template_one",
                "email_template_two",
                "letter_template_one",
                "letter_template_two",
            ],
        ),
        (
            create_active_user_view_permissions(),
            "Templates",
            {"template_type": "sms"},
            ["All", "Email", "Letter"],
            ["sms_template_one", "sms_template_two"],
        ),
        (
            create_active_user_view_permissions(),
            "Templates",
            {"template_type": "email"},
            ["All", "Text message", "Letter"],
            ["email_template_one", "email_template_two"],
        ),
        (
            create_active_user_view_permissions(),
            "Templates",
            {"template_type": "letter"},
            ["All", "Email", "Text message"],
            ["letter_template_one", "letter_template_two"],
        ),
        (
            create_active_caseworking_user(),
            "Templates",
            {},
            ["Email", "Text message", "Letter"],
            [
                "sms_template_one",
                "sms_template_two",
                "email_template_one",
                "email_template_two",
                "letter_template_one",
                "letter_template_two",
            ],
        ),
        (
            create_active_caseworking_user(),
            "Templates",
            {"template_type": "email"},
            ["All", "Text message", "Letter"],
            ["email_template_one", "email_template_two"],
        ),
    ],
)
def test_should_show_page_for_choosing_a_template(
    client_request,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_no_api_keys,
    extra_args,
    expected_nav_links,
    expected_templates,
    service_one,
    user,
    expected_page_title,
):
    service_one["permissions"].append("letter")
    client_request.login(user)

    page = client_request.get("main.choose_template", service_id=service_one["id"], **extra_args)

    assert normalize_spaces(page.select_one("h1").text) == expected_page_title

    links_in_page = page.select(".pill a:not(.pill-item--selected)")

    assert len(links_in_page) == len(expected_nav_links)

    for index, expected_link in enumerate(expected_nav_links):
        assert links_in_page[index].text.strip() == expected_link

    template_links = page.select("#template-list .govuk-label a, .template-list-item a")

    assert len(template_links) == len(expected_templates)

    for index, expected_template in enumerate(expected_templates):
        assert template_links[index].text.strip() == expected_template

    mock_get_service_templates.assert_called_once_with(SERVICE_ONE_ID)
    mock_get_template_folders.assert_called_once_with(SERVICE_ONE_ID)


def test_choose_template_can_pass_through_an_initial_state_to_templates_and_folders_selection_form(
    client_request,
    mock_get_template_folders,
    mock_get_service_templates,
    mock_get_no_api_keys,
):
    page = client_request.get("main.choose_template", service_id=SERVICE_ONE_ID, initial_state="add-new-template")

    templates_and_folders_form = page.select_one("form")
    assert templates_and_folders_form["data-prev-state"] == "add-new-template"


def test_should_not_show_template_nav_if_only_one_type_of_template(
    client_request,
    mock_get_template_folders,
    mock_get_service_templates_with_only_one_template,
    mock_get_no_api_keys,
):
    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )

    assert not page.select(".pill")


def test_should_not_show_live_search_if_list_of_templates_fits_onscreen(
    client_request,
    mock_get_template_folders,
    mock_get_service_templates,
    mock_get_no_api_keys,
):
    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )

    assert not page.select(".live-search")


def test_should_show_live_search_if_list_of_templates_taller_than_screen(
    client_request,
    mock_get_template_folders,
    mock_get_more_service_templates_than_can_fit_onscreen,
    mock_get_no_api_keys,
):
    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )
    search = page.select_one(".live-search")

    assert search["data-notify-module"] == "live-search"
    assert search["data-targets"] == "#template-list .template-list-item"
    assert normalize_spaces(search.select_one("label").text) == "Search by name"

    assert len(page.select(search["data-targets"])) == len(page.select("#template-list .govuk-label")) == 14


def test_should_label_search_by_id_for_services_with_api_keys(
    client_request,
    mock_get_template_folders,
    mock_get_more_service_templates_than_can_fit_onscreen,
    mock_get_api_keys,
):
    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )
    assert normalize_spaces(page.select_one(".live-search label").text) == "Search by name or ID"


def test_should_show_live_search_if_service_has_lots_of_folders(
    client_request,
    mock_get_template_folders,
    mock_get_service_templates,  # returns 4 templates
    mock_get_no_api_keys,
):
    mock_get_template_folders.return_value = [
        _folder("one", PARENT_FOLDER_ID),
        _folder("two", None, parent=PARENT_FOLDER_ID),
        _folder("three", None, parent=PARENT_FOLDER_ID),
        _folder("four", None, parent=PARENT_FOLDER_ID),
    ]

    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )

    count_of_templates_and_folders = len(page.select("#template-list .govuk-label"))
    count_of_folders = len(page.select(".template-list-folder:first-of-type"))
    count_of_templates = count_of_templates_and_folders - count_of_folders

    assert len(page.select(".live-search")) == 1
    assert count_of_folders == 4
    assert count_of_templates == 4


@pytest.mark.parametrize(
    "service_permissions, expected_values, expected_labels",
    (
        pytest.param(
            ["email", "sms"],
            [
                "email",
                "sms",
                "copy-existing",
            ],
            [
                "Email",
                "Text message",
                "Copy an existing template",
            ],
        ),
        pytest.param(
            ["email", "sms", "letter"],
            [
                "email",
                "sms",
                "letter",
                "copy-existing",
            ],
            [
                "Email",
                "Text message",
                "Letter",
                "Copy an existing template",
            ],
        ),
    ),
)
def test_should_show_new_template_choices_if_service_has_folder_permission(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_no_api_keys,
    service_permissions,
    expected_values,
    expected_labels,
):
    service_one["permissions"] = service_permissions

    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )

    if not page.select("#add_new_template_form"):
        raise ElementNotFound

    assert normalize_spaces(page.select_one("#add_new_template_form fieldset legend").text) == "New template"
    assert [choice["value"] for choice in page.select("#add_new_template_form input[type=radio]")] == expected_values
    assert [normalize_spaces(choice.text) for choice in page.select("#add_new_template_form label")] == expected_labels


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "custom_email_sender_name, expected_email_from",
    (
        (None, "service one"),
        ("custom", "custom"),
    ),
)
def test_should_show_page_for_email_template(
    client_request,
    mock_get_service_email_template,
    service_one,
    fake_uuid,
    custom_email_sender_name,
    expected_email_from,
):
    service_one["custom_email_sender_name"] = custom_email_sender_name
    page = client_request.get(
        ".view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert [
        (normalize_spaces(row.select_one("dt").text), normalize_spaces(row.select_one("dd").text))
        for row in page.select(".email-message-meta .govuk-summary-list__row")
    ] == [
        ("From", expected_email_from),
        ("To", "email address"),
        ("Subject", "Your ((thing)) is due soon"),
    ]
    assert normalize_spaces(page.select_one(".email-message-body").text) == "Your vehicle tax expires on ((date))"


@pytest.mark.parametrize(
    "permissions, template_content, expected_hint_text",
    (
        (
            {},
            "Hello world",
            "",
        ),
        (
            {"view_activity"},
            "Hello ((name)) today is ((day of week))",
            "",
        ),
        (
            {"manage_templates"},
            "Hello world",
            "Will be charged as 1 text message",
        ),
        (
            {"manage_service"},
            "Hello ((name)) today is ((day of week))",
            "Will be charged as 1 text message (not including personalisation)",
        ),
        (
            {"manage_api_keys"},
            "a" * 919,
            # This is one character more than our max (918) but we don’t want to show an error here
            "Will be charged as 7 text messages",
        ),
    ),
)
def test_should_show_page_for_sms_template(
    client_request,
    mock_get_service_template,
    service_one,
    fake_uuid,
    active_user_with_permissions,
    permissions,
    template_content,
    expected_hint_text,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={"data": create_template(template_id=fake_uuid, template_type="sms", content=template_content)},
    )
    active_user_with_permissions["permissions"][SERVICE_ONE_ID] = permissions
    client_request.login(active_user_with_permissions)
    page = client_request.get(
        ".view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one(".sms-message-recipient").text) == "To: phone number"
    assert normalize_spaces(page.select_one(".sms-message-wrapper").text) == f"service one: {template_content}"
    assert normalize_spaces(getattr(page.select_one(".govuk-hint"), "text", "")) == expected_hint_text


def test_should_show_page_for_one_template(
    client_request,
    mock_get_service_template,
    fake_uuid,
):
    template_id = fake_uuid
    page = client_request.get(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=template_id,
    )

    back_link = page.select_one(".govuk-back-link")
    assert back_link["href"] == url_for(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=template_id,
    )

    assert page.select_one("input[type=text]")["value"] == "Two week reminder"
    assert "Template &lt;em&gt;content&lt;/em&gt; with &amp; entity" in str(page.select_one("textarea"))
    assert page.select_one("textarea")["data-notify-module"] == "enhanced-textbox"
    assert page.select_one("textarea")["data-highlight-placeholders"] == "true"

    assert (
        (page.select_one("[data-notify-module=update-status]")["data-target"])
        == (page.select_one("textarea")["id"])
        == "template_content"
    )

    assert (page.select_one("[data-notify-module=update-status]")["data-updates-url"]) == url_for(
        ".count_content_length",
        service_id=SERVICE_ONE_ID,
        template_type="sms",
    )

    assert (page.select_one("[data-notify-module=update-status]")["aria-live"]) == "polite"

    mock_get_service_template.assert_called_with(SERVICE_ONE_ID, template_id, None)


@pytest.mark.parametrize(
    "template_type",
    (
        "email",
        pytest.param("sms", marks=pytest.mark.xfail),
        pytest.param("letter", marks=pytest.mark.xfail),
    ),
)
def test_edit_email_template_should_have_unsubscribe_checkbox(
    client_request,
    fake_uuid,
    template_type,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={"data": create_template(template_id=fake_uuid, template_type=template_type)},
    )
    page = client_request.get(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )
    assert page.select_one("form input[type=checkbox]")["name"] == "has_unsubscribe_link"
    assert normalize_spaces(page.select_one("form label[for=has_unsubscribe_link]").text) == "Add an unsubscribe link"
    assert (
        normalize_spaces(
            page.select_one(".govuk-checkboxes__item--single-with-hint #has_unsubscribe_link-item-hint").text
        )
        == "You will see unsubscribe requests on the dashboard"
    )


@pytest.mark.parametrize(
    "post_data, expected_unsubscribeable",
    (
        (
            {
                "has_unsubscribe_link": True,
            },
            True,
        ),
        ({}, False),
    ),
)
def test_edit_email_template_should_update_unsubscribe(
    client_request,
    platform_admin_user,
    mock_update_service_template,
    post_data,
    expected_unsubscribeable,
    fake_uuid,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={"data": create_template(template_id=fake_uuid, template_type="email")},
    )
    client_request.login(platform_admin_user)
    client_request.post(".edit_service_template", service_id=SERVICE_ONE_ID, template_id=fake_uuid, _data=post_data)
    mock_update_service_template.assert_called_once_with(
        content="Template content",
        name="sample template",
        service_id=SERVICE_ONE_ID,
        subject="Template subject",
        template_id=fake_uuid,
        has_unsubscribe_link=expected_unsubscribeable,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "template_type",
    (
        "email",
        pytest.param("sms", marks=pytest.mark.xfail()),
    ),
)
def test_add_email_template_should_have_unsubscribe_checkbox(
    client_request,
    template_type,
):
    page = client_request.get(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type=template_type,
    )
    assert page.select_one("form input[type=checkbox]")["name"] == "has_unsubscribe_link"
    assert normalize_spaces(page.select_one("form label[for=has_unsubscribe_link]").text) == "Add an unsubscribe link"
    assert (
        normalize_spaces(
            page.select_one(".govuk-checkboxes__item--single-with-hint #has_unsubscribe_link-item-hint").text
        )
        == "You will see unsubscribe requests on the dashboard"
    )


def test_add_email_template_should_add_unsubscribe(
    client_request,
    platform_admin_user,
    mock_create_service_template,
    mocker,
):
    client_request.login(platform_admin_user)
    client_request.post(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type="email",
        _data={
            "name": "foo",
            "subject": "bar",
            "has_unsubscribe_link": True,
            "template_content": "baz",
        },
    )
    mock_create_service_template.assert_called_once_with(
        type_="email",
        name="foo",
        subject="bar",
        content="baz",
        service_id=SERVICE_ONE_ID,
        parent_folder_id=None,
        has_unsubscribe_link=True,
    )


def test_editing_letter_template_should_have_hidden_name_field(
    client_request, mock_get_service_letter_template, fake_uuid, service_one
):
    service_one["permissions"].append("letter")
    template_id = fake_uuid
    page = client_request.get(".edit_service_template", service_id=SERVICE_ONE_ID, template_id=template_id)

    name_input = page.select_one("input[name=name]")
    assert name_input["value"] == "Two week reminder"
    assert name_input["type"] == "hidden"


def test_GET_edit_service_template_for_welsh_letter(
    client_request, mock_get_service_letter_template_welsh_language, fake_uuid, service_one
):
    service_one["permissions"].append("letter")
    template_id = fake_uuid
    page = client_request.get(
        ".edit_service_template", service_id=SERVICE_ONE_ID, template_id=template_id, language="welsh"
    )

    subject_label = page.select_one("label[for=subject]")
    assert subject_label.text.strip() == "Heading (Welsh)"

    content_label = page.select_one("label[for=template_content]")
    assert content_label.text.strip() == "Body text (Welsh)"


def test_caseworker_redirected_to_set_sender_for_one_off(
    client_request,
    mock_get_service_template,
    fake_uuid,
    active_caseworking_user,
):
    client_request.login(active_caseworking_user)
    client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.set_sender",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2020-01-01 15:00")
def test_caseworker_sees_template_page_if_template_is_deleted(
    client_request,
    mock_get_deleted_template,
    fake_uuid,
    mocker,
    active_caseworking_user,
):
    mocker.patch("app.user_api_client.get_user", return_value=active_caseworking_user)

    template_id = fake_uuid
    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=template_id,
        _test_page_title=False,
    )

    content = str(page)
    assert url_for("main.send_one_off", service_id=SERVICE_ONE_ID, template_id=fake_uuid) not in content
    assert page.select("p.hint")[0].text.strip() == "This template was deleted today at 3:00pm."

    mock_get_deleted_template.assert_called_with(SERVICE_ONE_ID, template_id, None)


def test_user_with_only_send_and_view_redirected_to_set_sender_for_one_off(
    client_request,
    mock_get_service_template,
    active_user_with_permissions,
    fake_uuid,
):
    active_user_with_permissions["permissions"][SERVICE_ONE_ID] = [
        "send_messages",
        "view_activity",
    ]
    client_request.login(active_user_with_permissions)
    client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.set_sender",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "permissions",
    (
        pytest.param({"manage_templates"}),
        pytest.param({"send_messages", "view_activity", "manage_settings"}, marks=pytest.mark.xfail),
    ),
)
@pytest.mark.parametrize(
    "template_type",
    (
        pytest.param("letter"),
        pytest.param("email", marks=pytest.mark.xfail),
        pytest.param("sms", marks=pytest.mark.xfail),
    ),
)
def test_letter_page_has_rename_link(
    client_request,
    mock_get_service_letter_template,
    single_letter_contact_block,
    active_user_with_permissions,
    mocker,
    fake_uuid,
    permissions,
    template_type,
    mock_get_page_counts_for_letter,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={"data": create_template(template_id=fake_uuid, template_type=template_type)},
    )
    active_user_with_permissions["permissions"][SERVICE_ONE_ID] = permissions
    client_request.login(active_user_with_permissions)
    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )
    first_row = page.select_one("main > .govuk-grid-row")
    folder_nav = first_row.select_one(".govuk-grid-column-five-sixths")
    link = first_row.select_one(".govuk-grid-column-one-sixth a.govuk-link.folder-heading-manage-link")

    assert normalize_spaces(folder_nav.text) == "Templates sample template"

    assert normalize_spaces(link.text) == "Rename this template"
    assert link["href"] == url_for(
        "main.rename_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "permissions",
    (
        {"send_messages", "view_activity"},
        {"send_messages"},
        {"view_activity"},
        {},
    ),
)
def test_user_with_only_send_and_view_sees_letter_page(
    client_request,
    mock_get_service_letter_template,
    single_letter_contact_block,
    active_user_with_permissions,
    fake_uuid,
    permissions,
    mock_get_page_counts_for_letter,
):
    active_user_with_permissions["permissions"][SERVICE_ONE_ID] = permissions
    client_request.login(active_user_with_permissions)
    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )
    assert normalize_spaces(page.select_one(".folder-heading-breadcrumb").text) == "Templates"
    assert normalize_spaces(page.select_one("h1").text) == "Two week reminder"
    assert normalize_spaces(page.select_one("title").text) == (
        "Two week reminder – Templates – service one – GOV.UK Notify"
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "letter_branding, expected_link, expected_link_text",
    (
        (
            None,
            partial(url_for, "main.letter_branding_options", service_id=SERVICE_ONE_ID, from_template=TEMPLATE_ONE_ID),
            "Add logo",
        ),
        (
            TEMPLATE_ONE_ID,
            partial(url_for, "main.edit_template_postage", template_id=TEMPLATE_ONE_ID),
            "Change postage",
        ),
    ),
)
@pytest.mark.parametrize(
    "user_has_manage_settings_permission",
    (True, pytest.mark.xfail(False)),
)
def test_letter_with_default_branding_has_add_logo_button(
    client_request,
    service_one,
    mock_get_service_letter_template,
    single_letter_contact_block,
    letter_branding,
    expected_link,
    expected_link_text,
    mock_get_page_counts_for_letter,
    user_has_manage_settings_permission,
    active_user_with_permissions,
):
    service_one["permissions"] += ["letter"]
    service_one["letter_branding"] = letter_branding

    if not user_has_manage_settings_permission:
        active_user_with_permissions["permissions"].remove("manage_settings")

    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=TEMPLATE_ONE_ID,
        _test_page_title=False,
    )

    edit_links = page.select(".template-container a")
    assert edit_links[0]["href"] == expected_link(service_id=SERVICE_ONE_ID)
    assert edit_links[0].text == expected_link_text


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "template_postage,expected_result",
    [
        ("first", "Postage: first class"),
        ("second", "Postage: second class"),
    ],
)
def test_view_letter_template_displays_postage(
    client_request,
    service_one,
    mock_get_template_folders,
    single_letter_contact_block,
    active_user_with_permissions,
    mocker,
    fake_uuid,
    template_postage,
    expected_result,
    mock_get_page_counts_for_letter,
):
    client_request.login(active_user_with_permissions)
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={"data": create_template(template_type="letter", postage=template_postage)},
    )

    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one(".letter-postage").text) == expected_result


def test_view_non_letter_template_does_not_display_postage(
    client_request,
    mock_get_service_template,
    fake_uuid,
):
    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )
    assert "Postage" not in page.text


def test_view_letter_template_does_not_display_send_button_if_template_over_10_pages_long(
    client_request,
    service_one,
    single_letter_contact_block,
    active_user_with_permissions,
    mocker,
    fake_uuid,
):
    do_mock_get_page_counts_for_letter(mocker, count=11)
    client_request.login(active_user_with_permissions)
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={"data": create_template(template_type="letter", postage="second")},
    )

    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert "Get ready to send" not in page.text
    assert page.select_one("h1", {"data-error-type": "letter-too-long"})


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_view_letter_template_displays_change_language_button(
    client_request,
    service_one,
    single_letter_contact_block,
    active_user_with_permissions,
    mocker,
    fake_uuid,
    mock_get_page_counts_for_letter,
):
    client_request.login(active_user_with_permissions)
    template_id = fake_uuid
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={"data": create_template(template_type="letter", template_id=template_id)},
    )
    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=template_id,
        _test_page_title=False,
    )

    change_language_button = page.select_one(".change-language")

    assert normalize_spaces(change_language_button.text) == "Change language"
    assert change_language_button["href"] == url_for(
        "main.letter_template_change_language", service_id=SERVICE_ONE_ID, template_id=template_id
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_GET_letter_template_change_language(
    client_request, service_one, fake_uuid, mock_get_service_letter_template, active_user_with_permissions
):
    client_request.login(active_user_with_permissions)
    page = client_request.get(
        "main.letter_template_change_language",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    assert page.select_one("h1").text.strip() == "Change language"

    assert [label.text.strip() for label in page.select(".govuk-radios__item label")] == [
        "English only",
        "Welsh followed by English",
    ]
    assert [radio["value"] for radio in page.select(".govuk-radios__item input")] == [
        "english",
        "welsh_then_english",
    ]

    assert page.select("form button")

    mock_get_service_letter_template.assert_called_once_with(SERVICE_ONE_ID, fake_uuid, None)

    assert (
        page.select_one("a[class='govuk-back-link']").get("href") == f"/services/{SERVICE_ONE_ID}/templates/{fake_uuid}"
    )


def test_GET_letter_template_change_language_404s_if_template_is_not_a_letter(
    client_request,
    service_one,
    mock_get_service_template,
    active_user_with_permissions,
    fake_uuid,
):
    client_request.login(active_user_with_permissions)
    page = client_request.get(
        "main.letter_template_change_language", service_id=SERVICE_ONE_ID, template_id=fake_uuid, _expected_status=404
    )

    assert page.select_one("h1").text.strip() != "Change language"


def test_POST_letter_template_change_to_welsh_and_english_sets_subject_and_content(
    client_request,
    service_one,
    mocker,
    fake_uuid,
    active_user_with_permissions,
    mock_get_service_letter_template,
):
    client_request.login(active_user_with_permissions)

    mock_template_change_language = mocker.patch(
        "app.main.views_nl.templates.service_api_client.update_service_template"
    )

    client_request.post(
        "main.letter_template_change_language",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={"languages": "welsh_then_english"},
        _expected_redirect=url_for(
            "main.view_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )
    mock_template_change_language.assert_called_with(
        SERVICE_ONE_ID,
        fake_uuid,
        letter_languages="welsh_then_english",
        letter_welsh_subject="Welsh heading",
        letter_welsh_content="Welsh body text",
    )


@pytest.mark.parametrize(
    "subject, content, extra_kwargs",
    (
        ("Heading", "Body text", {"subject": "English heading", "content": "English body text"}),
        ("Some custom heading", "Body text", {"content": "English body text"}),
        ("Heading", "Some custom body", {"subject": "English heading"}),
        ("Some custom heading", "Some custom body", {}),
    ),
)
def test_POST_letter_template_change_to_welsh_and_english_resets_english_subject_and_content(
    client_request,
    service_one,
    mocker,
    fake_uuid,
    active_user_with_permissions,
    subject,
    content,
    extra_kwargs,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": template_json(
                service_id=SERVICE_ONE_ID,
                id_=fake_uuid,
                name="Two week reminder",
                type_="letter",
                content=content,
                subject=subject,
                postage="second",
            )
        },
    )

    client_request.login(active_user_with_permissions)

    mock_template_change_language = mocker.patch(
        "app.main.views_nl.templates.service_api_client.update_service_template"
    )

    client_request.post(
        "main.letter_template_change_language",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={"languages": "welsh_then_english"},
        _expected_redirect=url_for(
            "main.view_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )
    mock_template_change_language.assert_called_with(
        SERVICE_ONE_ID,
        fake_uuid,
        letter_languages="welsh_then_english",
        letter_welsh_subject="Welsh heading",
        letter_welsh_content="Welsh body text",
        **extra_kwargs,
    )


def test_POST_letter_template_change_to_english_redirects_to_confirmation_page(
    client_request,
    service_one,
    mocker,
    fake_uuid,
    active_user_with_permissions,
    mock_get_service_letter_template_welsh_language,
):
    client_request.login(active_user_with_permissions)

    mock_template_change_language = mocker.patch(
        "app.main.views_nl.templates.service_api_client.update_service_template"
    )

    client_request.post(
        "main.letter_template_change_language",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={"languages": "english"},
        _expected_redirect=url_for(
            "main.letter_template_confirm_remove_welsh", service_id=SERVICE_ONE_ID, template_id=fake_uuid
        ),
    )
    assert mock_template_change_language.call_args_list == []


def test_GET_letter_template_confirm_remove_welsh(
    client_request,
    service_one,
    mocker,
    fake_uuid,
    active_user_with_permissions,
    mock_get_service_letter_template,
):
    client_request.login(active_user_with_permissions)

    mock_template_change_language = mocker.patch(
        "app.main.views_nl.templates.service_api_client.update_service_template"
    )

    page = client_request.get(
        "main.letter_template_confirm_remove_welsh",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )
    form = page.select_one("form[method=post]")
    assert form.select_one("button")
    assert mock_template_change_language.call_args_list == []


def test_POST_letter_template_confirm_remove_welsh(
    client_request,
    service_one,
    mocker,
    fake_uuid,
    active_user_with_permissions,
    mock_get_service_letter_template,
):
    client_request.login(active_user_with_permissions)

    mock_template_change_language = mocker.patch(
        "app.main.views_nl.templates.service_api_client.update_service_template"
    )

    client_request.post(
        "main.letter_template_confirm_remove_welsh",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={"confirm": "true"},
        _expected_redirect=url_for(
            "main.view_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )
    mock_template_change_language.assert_called_with(
        SERVICE_ONE_ID,
        fake_uuid,
        letter_languages="english",
        letter_welsh_subject=None,
        letter_welsh_content=None,
    )


@pytest.mark.parametrize(
    "subject, content, extra_kwargs",
    (
        ("English heading", "English body text", {"subject": "Heading", "content": "Body text"}),
        ("Some custom heading", "English body text", {"content": "Body text"}),
        ("English heading", "Some custom body", {"subject": "Heading"}),
        ("Some custom heading", "Some custom body", {}),
    ),
)
def test_POST_letter_template_confirm_remove_welsh_resets_english_subject_and_content(
    client_request,
    service_one,
    mocker,
    fake_uuid,
    active_user_with_permissions,
    subject,
    content,
    extra_kwargs,
):
    def _get(service_id, template_id, version=None, postage="second"):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="Two week reminder",
            type_="letter",
            content=content,
            subject=subject,
            postage=postage,
        )
        return {"data": template}

    mocker.patch("app.service_api_client.get_service_template", side_effect=_get)

    client_request.login(active_user_with_permissions)

    mock_template_change_language = mocker.patch(
        "app.main.views_nl.templates.service_api_client.update_service_template"
    )

    client_request.post(
        "main.letter_template_confirm_remove_welsh",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={"confirm": "true"},
        _expected_redirect=url_for(
            "main.view_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )
    mock_template_change_language.assert_called_with(
        SERVICE_ONE_ID,
        fake_uuid,
        letter_languages="english",
        letter_welsh_subject=None,
        letter_welsh_content=None,
        **extra_kwargs,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_GET_letter_template_attach_pages(client_request, service_one, fake_uuid, mock_get_service_letter_template):
    page = client_request.get(
        "main.letter_template_attach_pages",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    assert page.select_one("h1").text.strip() == "Attach pages"
    assert page.select_one("input.file-upload-field")
    assert page.select_one("input.file-upload-field")["accept"] == ".pdf"
    assert page.select("form button")
    assert normalize_spaces(page.select_one("input[type=file]")["data-button-text"]) == "Choose a file"

    mock_get_service_letter_template.assert_called_once_with(SERVICE_ONE_ID, fake_uuid, None)


def test_GET_letter_template_attach_pages_404s_if_invalid_template_id(client_request, service_one, fake_uuid, mocker):
    mocker.patch(
        "app.notify_client.service_api_client.service_api_client.get_service_template",
        side_effect=HTTPError(response=Mock(status_code=404)),
    )
    client_request.get(
        "main.letter_template_attach_pages", service_id=SERVICE_ONE_ID, template_id=fake_uuid, _expected_status=404
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_post_attach_pages_errors_when_content_outside_printable_area(
    client_request,
    fake_uuid,
    service_one,
    mock_get_service_letter_template,
    mocker,
):
    mocker.patch("uuid.uuid4", return_value=fake_uuid)
    mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    # page count for the attachment
    mocker.patch("app.main.views_nl.templates.pdf_page_count", return_value=1)

    mock_s3_upload = mocker.patch("app.main.views_nl.templates.upload_letter_to_s3")

    mock_sanitise_response = Mock()
    mock_sanitise_response.raise_for_status.side_effect = RequestException(response=Mock(status_code=400))
    mock_sanitise_response.json = lambda: {"message": "content-outside-printable-area", "invalid_pages": [1]}
    mocker.patch("app.template_preview_client.sanitise_letter", return_value=mock_sanitise_response)

    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        file_contents = file.read()
        file.seek(0)

        page = client_request.post(
            "main.letter_template_attach_pages",
            service_id=SERVICE_ONE_ID,
            template_id=sample_uuid(),
            _data={"file": file},
            _expected_status=400,
        )

        mock_s3_upload.assert_called_once_with(
            file_contents,
            file_location=f"service-{SERVICE_ONE_ID}/{fake_uuid}.pdf",
            status="invalid",
            page_count=1,
            filename="tests/test_pdf_files/one_page_pdf.pdf",
            invalid_pages=[1],
            message="content-outside-printable-area",
        )

    assert page.select_one(".banner-dangerous h1").text == "Your content is outside the printable area"
    assert (
        page.select_one(".banner-dangerous p").text
        == "You need to edit page 1.Files must meet our letter specification (opens in a new tab)."
    )
    assert page.select_one("form").attrs["action"] == url_for(
        "main.letter_template_attach_pages", service_id=SERVICE_ONE_ID, template_id=sample_uuid()
    )
    assert normalize_spaces(page.select_one("input[type=file]")["data-button-text"]) == "Upload your file again"

    letter_images = page.select("main img")
    assert len(letter_images) == 1
    assert letter_images[0]["src"] == url_for(
        "no_cookie.view_invalid_letter_attachment_as_preview", service_id=SERVICE_ONE_ID, file_id=fake_uuid, page=1
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_post_attach_pages_errors_when_base_template_plus_attachment_too_long(
    client_request,
    api_user_active,
    fake_uuid,
    service_one,
    mocker,
):
    mocker.patch("uuid.uuid4", return_value=fake_uuid)
    mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    mocker.patch("app.main.views_nl.templates.upload_letter_to_s3")
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": template_version_json(SERVICE_ONE_ID, fake_uuid, api_user_active, version=1, type_="letter")
        },
    )
    mocker.patch("app.template_preview_client.sanitise_letter")
    do_mock_get_page_counts_for_letter(mocker, count=9)

    with open("tests/test_pdf_files/multi_page_pdf.pdf", "rb") as file:
        page = client_request.post(
            "main.letter_template_attach_pages",
            service_id=SERVICE_ONE_ID,
            template_id=sample_uuid(),
            _data={"file": file},
            _expected_status=400,
        )

    assert page.select_one(".banner-dangerous h1").text == "There is a problem"
    assert page.select_one(".banner-dangerous p").text == (
        "Letters must be 10 pages or less (5 double-sided sheets of paper). "
        "In total, your letter template and the file you attached are 19 pages long."
    )
    assert page.select_one("form").attrs["action"] == url_for(
        "main.letter_template_attach_pages", service_id=SERVICE_ONE_ID, template_id=sample_uuid()
    )
    assert normalize_spaces(page.select_one("input[type=file]")["data-button-text"]) == "Upload your file again"


@pytest.mark.parametrize("page_count", [1, 2])
def test_post_attach_pages_redirects_to_template_view_when_validation_successful(
    client_request,
    service_one,
    mock_get_service_letter_template,
    page_count,
    mock_get_page_counts_for_letter,
    mocker,
):
    mocker.patch("app.extensions.antivirus_client.scan", return_value=True)

    mock_sanitise = mocker.patch("app.template_preview_client.sanitise_letter")

    # page count for the attachment
    mocker.patch("app.main.views_nl.templates.pdf_page_count", return_value=page_count)

    mock_save = mocker.patch("app.main.views_nl.templates._save_letter_attachment")

    template_id = sample_uuid()
    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        client_request.post(
            "main.letter_template_attach_pages",
            service_id=SERVICE_ONE_ID,
            template_id=template_id,
            _data={"file": file},
            _expected_redirect=url_for(
                "main.view_template",
                service_id=SERVICE_ONE_ID,
                template_id=template_id,
                _anchor="first-page-of-attachment",
            ),
        )

    upload_id = mock_sanitise.call_args[1]["upload_id"]

    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        mock_save.assert_called_once_with(
            service_id=service_one["id"],
            template_id=template_id,
            upload_id=upload_id,
            original_filename="tests/test_pdf_files/one_page_pdf.pdf",
            original_file=file.read(),
            sanitise_response=mock_sanitise.return_value,
        )


def test_post_attach_pages_archives_existing_attachment_when_it_exists(
    client_request,
    service_one,
    active_user_with_permissions,
    mock_get_service_letter_template_with_attachment,
    mock_get_page_counts_for_letter,
    mocker,
):
    mocker.patch("app.extensions.antivirus_client.scan", return_value=True)

    mock_sanitise = mocker.patch("app.template_preview_client.sanitise_letter")

    # page count for the attachment
    mocker.patch("app.main.views_nl.templates.pdf_page_count", return_value=1)

    mock_save = mocker.patch("app.main.views_nl.templates._save_letter_attachment")

    mock_archive_attachment = mocker.patch("app.letter_attachment_client.archive_letter_attachment")

    template_id = sample_uuid()
    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        client_request.post(
            "main.letter_template_attach_pages",
            service_id=SERVICE_ONE_ID,
            template_id=template_id,
            _data={"file": file},
            _expected_redirect=url_for(
                "main.view_template",
                service_id=SERVICE_ONE_ID,
                template_id=template_id,
                _anchor="first-page-of-attachment",
            ),
        )

    upload_id = mock_sanitise.call_args[1]["upload_id"]

    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        mock_save.assert_called_once_with(
            service_id=service_one["id"],
            template_id=template_id,
            upload_id=upload_id,
            original_filename="tests/test_pdf_files/one_page_pdf.pdf",
            original_file=file.read(),
            sanitise_response=mock_sanitise.return_value,
        )

    mock_archive_attachment.assert_called_once_with(
        letter_attachment_id=sample_uuid(),
        user_id=active_user_with_permissions["id"],
        service_id=SERVICE_ONE_ID,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_post_attach_pages_doesnt_replace_existing_attachment_if_new_attachment_errors(
    client_request,
    fake_uuid,
    service_one,
    mock_get_service_letter_template_with_attachment,
    mocker,
):
    mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    mocker.patch("uuid.uuid4", return_value=fake_uuid)

    mock_sanitise_response = Mock()
    mock_sanitise_response.raise_for_status.side_effect = RequestException(response=Mock(status_code=400))
    mock_sanitise_response.json = lambda: {"message": "content-outside-printable-area", "invalid_pages": [1]}
    mocker.patch("app.template_preview_client.sanitise_letter", return_value=mock_sanitise_response)

    mocker.patch("app.main.views_nl.templates.upload_letter_to_s3")
    mocker.patch("app.main.views_nl.templates.pdf_page_count", return_value=1)

    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        page = client_request.post(
            "main.letter_template_attach_pages",
            service_id=SERVICE_ONE_ID,
            template_id=sample_uuid(),
            _data={"file": file},
            _expected_status=200,
        )

    assert page.select_one(".banner-dangerous h1").text == "Your content is outside the printable area"

    cancel_link = page.select_one(".file-upload-alternate-link a.govuk-link")
    assert normalize_spaces(cancel_link.text) == "cancel"
    assert cancel_link["href"] == url_for(
        "main.letter_template_attach_pages",
        service_id=SERVICE_ONE_ID,
        template_id=sample_uuid(),
    )
    # Should not have a ‘Remove attachment’ link
    assert not page.select(".js-stick-at-bottom-when-scrolling .govuk-link--destructive")

    # should show preview of invalid attachment
    letter_images = page.select("main img")
    assert len(letter_images) == 1
    assert letter_images[0]["src"] == url_for(
        "no_cookie.view_invalid_letter_attachment_as_preview", service_id=SERVICE_ONE_ID, file_id=fake_uuid, page=1
    )


def test_save_letter_attachment_saves_to_s3_and_db_and_redirects(notify_admin, service_one, mocker):
    upload_id = uuid.uuid4()
    template_id = uuid.uuid4()

    attachment_page_count = 3

    mock_sanitise_response = Mock(
        content="The sanitised content",
        json=Mock(return_value={"file": "VGhlIHNhbml0aXNlZCBjb250ZW50", "page_count": attachment_page_count}),
    )

    mock_upload = mocker.patch("app.main.views_nl.templates.upload_letter_attachment_to_s3")
    mock_backup = mocker.patch("app.main.views_nl.templates.backup_original_letter_to_s3")
    mock_save_to_db = mocker.patch("app.letter_attachment_client.create_letter_attachment")

    g.current_service = Service(service_one)

    _save_letter_attachment(
        service_id=service_one["id"],
        template_id=template_id,
        upload_id=upload_id,
        original_filename="foo.pdf",
        original_file=b"the_original_file",
        sanitise_response=mock_sanitise_response,
    )

    mock_upload.assert_called_once_with(
        b"The sanitised content",
        file_location=f"service-{SERVICE_ONE_ID}/{upload_id}.pdf",
        page_count=attachment_page_count,
        original_filename="foo.pdf",
    )
    mock_backup.assert_called_once_with(b"the_original_file", upload_id=upload_id)
    mock_save_to_db.assert_called_once_with(
        upload_id=upload_id,
        template_id=template_id,
        service_id=service_one["id"],
        page_count=attachment_page_count,
        original_filename="foo.pdf",
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_attach_pages_with_letter_attachment_id_in_template_shows_manage_page(
    mock_get_service_letter_template_with_attachment, client_request, service_one
):
    page = client_request.get(
        "main.letter_template_attach_pages",
        service_id=SERVICE_ONE_ID,
        template_id=sample_uuid(),
        _expected_status=200,
    )
    assert page.select_one("h1").text.strip() == "original file.pdf"
    assert len(page.select(".letter")) == 1
    assert page.select_one(".letter img")["src"] == f"/services/{SERVICE_ONE_ID}/attachment/{sample_uuid()}.png?page=1"
    assert normalize_spaces(page.select_one("input[type=file]")["data-button-text"]) == "Choose a different file"
    assert not page.select_one(".file-upload-alternate-link")

    remove_attachment_link = page.select_one(".js-stick-at-bottom-when-scrolling .govuk-link--destructive")
    assert normalize_spaces(remove_attachment_link.text) == "Remove attachment"
    assert remove_attachment_link["href"] == url_for(
        "main.letter_template_edit_pages",
        service_id=SERVICE_ONE_ID,
        template_id=sample_uuid(),
    )


def test_post_delete_letter_attachment_calls_archive_letter_attachment(
    mock_get_service_letter_template_with_attachment,
    client_request,
    service_one,
    mocker,
    active_user_with_permissions,
):
    mock_archive_attachment = mocker.patch("app.letter_attachment_client.archive_letter_attachment")
    client_request.post(
        "main.letter_template_edit_pages",
        service_id=SERVICE_ONE_ID,
        template_id=sample_uuid(),
        _expected_status=302,
        expected_redirect=url_for(
            "main.view_template",
            service_id=SERVICE_ONE_ID,
            template_id=sample_uuid(),
        ),
    )

    mock_archive_attachment.assert_called_once_with(
        letter_attachment_id=sample_uuid(),
        user_id=active_user_with_permissions["id"],
        service_id=service_one["id"],
    )


def test_get_delete_letter_attachment_shows_confirmation(
    mock_get_service_letter_template_with_attachment,
    client_request,
    service_one,
    mocker,
):
    mock_flash = mocker.patch("app.main.views_nl.templates.flash")
    mocker.patch("app.letter_attachment_client.archive_letter_attachment")
    page = client_request.get(
        "main.letter_template_edit_pages",
        service_id=SERVICE_ONE_ID,
        template_id=sample_uuid(),
        _expected_status=200,
    )
    mock_flash.assert_called_once_with("Are you sure you want to remove the ‘original file.pdf’ attachment?", "remove")
    assert page.select_one("h1").text.strip() == "original file.pdf"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_edit_letter_template_postage_page_displays_correctly(
    client_request,
    service_one,
    fake_uuid,
    mocker,
    mock_get_service_letter_template,
):
    page = client_request.get(
        "main.edit_template_postage",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    assert page.select_one("h1").text.strip() == "Change postage"
    assert page.select("input[checked]")[0].attrs["value"] == "second"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_edit_letter_template_displays_all_postage_options(
    client_request,
    service_one,
    fake_uuid,
    mock_get_service_letter_template,
):
    page = client_request.get(
        "main.edit_template_postage",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    assert page.select_one("h1").text.strip() == "Change postage"
    assert page.select("input[checked]")[0].attrs["value"] == "second"

    assert len(page.select("input[type=radio]")) == 3

    assert [
        (radio["value"], page.select_one(f"label[for={radio['id']}]").text.strip())
        for radio in page.select("input[type=radio]")
    ] == [("first", "First class"), ("second", "Second class"), ("economy", "Economy mail")]


def test_edit_letter_template_postage_page_404s_if_template_is_not_a_letter(
    client_request,
    service_one,
    mock_get_service_template,
    active_user_with_permissions,
    fake_uuid,
):
    client_request.login(active_user_with_permissions)
    page = client_request.get(
        "main.edit_template_postage", service_id=SERVICE_ONE_ID, template_id=fake_uuid, _expected_status=404
    )

    assert page.select_one("h1").text.strip() != "Edit postage"


def test_edit_letter_templates_postage_updates_postage(
    client_request,
    service_one,
    mocker,
    fake_uuid,
    mock_get_service_letter_template,
):
    mock_update_template_postage = mocker.patch(
        "app.main.views_nl.templates.service_api_client.update_service_template"
    )

    client_request.post(
        "main.edit_template_postage",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={"postage": "first"},
    )
    mock_update_template_postage.assert_called_with(SERVICE_ONE_ID, fake_uuid, postage="first")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "permissions, links_to_be_shown, permissions_warning_to_be_shown",
    [
        (["view_activity"], [], "If you need to send this text message or edit this template, contact your manager."),
        (
            ["manage_api_keys"],
            [],
            None,
        ),
        (
            ["manage_templates"],
            [
                (".edit_service_template", "Edit this template"),
            ],
            None,
        ),
        (
            ["send_messages", "manage_templates"],
            [
                (".set_sender", "Get ready to send a message using this template"),
                (".edit_service_template", "Edit this template"),
            ],
            None,
        ),
    ],
)
def test_should_be_able_to_view_a_template_with_links(
    client_request,
    mock_get_service_template,
    active_user_with_permissions,
    single_letter_contact_block,
    fake_uuid,
    permissions,
    links_to_be_shown,
    permissions_warning_to_be_shown,
):
    active_user_with_permissions["permissions"][SERVICE_ONE_ID] = permissions + ["view_activity"]
    client_request.login(active_user_with_permissions)

    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one(".folder-heading-breadcrumb").text) == "Templates"
    assert normalize_spaces(page.select_one("h1").text) == "Two week reminder"
    assert normalize_spaces(page.select_one("title").text) == (
        "Two week reminder – Templates – service one – GOV.UK Notify"
    )

    assert [(link["href"], normalize_spaces(link.text)) for link in page.select(".pill-separate-item")] == [
        (
            url_for(
                endpoint,
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
            text,
        )
        for endpoint, text in links_to_be_shown
    ]

    assert normalize_spaces(page.select_one("main p").text) == (permissions_warning_to_be_shown or "To: phone number")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_be_able_to_view_a_letter_template_with_links(
    client_request,
    mock_get_service_letter_template,
    single_letter_contact_block,
    fake_uuid,
    mock_get_page_counts_for_letter,
    mocker,
):
    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert [(link["href"], normalize_spaces(link.text)) for link in page.select("a[class*=edit-template-link]")] == [
        (
            url_for(
                "main.letter_branding_options",
                service_id=SERVICE_ONE_ID,
                from_template=fake_uuid,
            ),
            "Add logo",
        ),
        (
            url_for(
                "main.edit_template_postage",
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
            "Change postage",
        ),
        (
            url_for(
                "main.set_sender",
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
            "Get ready to send a letter using this template",
        ),
        (
            url_for(
                "main.set_template_sender",
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
            "Change your contact details",
        ),
        (
            url_for(
                "main.edit_service_template",
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
            "Edit body text",
        ),
        (
            url_for(
                "main.letter_template_attach_pages",
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
            "Attach pages",
        ),
    ]


def test_should_not_be_able_to_view_edit_links_for_an_archived_letter_template(
    client_request,
    single_letter_contact_block,
    fake_uuid,
    mock_get_page_counts_for_letter,
    mocker,
):
    archived_letter_template = template_json(
        service_id=SERVICE_ONE_ID,
        id_=fake_uuid,
        name="Two week reminder",
        type_="letter",
        content="Your vehicle tax expires soon",
        redact_personalisation=False,
        archived=True,
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": archived_letter_template})

    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    page_links = {link["href"] for link in page.select("a")}

    edit_links = {
        url_for(
            "main.set_sender",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
        url_for(
            "main.letter_branding_options",
            service_id=SERVICE_ONE_ID,
            from_template=fake_uuid,
        ),
        url_for(
            "main.edit_template_postage",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
        url_for(
            "main.edit_service_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
        url_for(
            "main.set_template_sender",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
        url_for(
            "main.letter_template_attach_pages",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    }

    assert len(page_links & edit_links) == 0


def test_should_be_able_to_view_a_letter_template_with_bilingual_content(
    client_request,
    service_one,
    mock_get_service_letter_template_welsh_language,
    single_letter_contact_block,
    fake_uuid,
    mocker,
):
    do_mock_get_page_counts_for_letter(mocker, count=5, welsh_page_count=3)
    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )
    assert [(str(ele)) for ele in page.select(".letter img, .letter div")] == [
        (
            '<img alt="" loading="eager" '
            'src="/services/596364a0-858e-42c8-9062-a8fe822260eb/templates/6ce466d0-fd6a-11e5-82f5-e0accb9d11a6.png'
            '?page=1"/>'
        ),
        (
            '<img alt="" loading="lazy" '
            'src="/services/596364a0-858e-42c8-9062-a8fe822260eb/templates/6ce466d0-fd6a-11e5-82f5-e0accb9d11a6.png'
            '?page=2"/>'
        ),
        (
            '<img alt="" loading="lazy" '
            'src="/services/596364a0-858e-42c8-9062-a8fe822260eb/templates/6ce466d0-fd6a-11e5-82f5-e0accb9d11a6.png'
            '?page=3"/>'
        ),
        '<div id="first-page-of-english-in-bilingual-letter"></div>',
        (
            '<img alt="" loading="eager" '
            'src="/services/596364a0-858e-42c8-9062-a8fe822260eb/templates/6ce466d0-fd6a-11e5-82f5-e0accb9d11a6.png'
            '?page=4"/>'
        ),
        (
            '<img alt="" loading="lazy" '
            'src="/services/596364a0-858e-42c8-9062-a8fe822260eb/templates/6ce466d0-fd6a-11e5-82f5-e0accb9d11a6.png'
            '?page=5"/>'
        ),
    ]


def test_should_show_template_id_on_template_page(
    client_request,
    mock_get_service_template,
    mock_get_template_folders,
    fake_uuid,
):
    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )
    assert fake_uuid in page.select(".copy-to-clipboard__value")[0].text


def test_should_show_sms_template_with_downgraded_unicode_characters(
    client_request,
    mocker,
    service_one,
    single_letter_contact_block,
    fake_uuid,
):
    msg = "here:\tare some “fancy quotes” and zero\u200bwidth\u200bspaces"
    rendered_msg = 'here: are some "fancy quotes" and zerowidthspaces'

    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={"data": template_json(service_id=service_one["id"], id_=fake_uuid, type_="sms", content=msg)},
    )

    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert rendered_msg in page.text


@pytest.mark.parametrize(
    "contact_block_data, expected_partial_url",
    (
        (
            [],
            partial(
                url_for,
                "main.service_add_letter_contact",
                from_template=sample_uuid(),
            ),
        ),
        (
            [create_letter_contact_block()],
            partial(
                url_for,
                "main.set_template_sender",
                template_id=sample_uuid(),
            ),
        ),
    ),
)
def test_should_let_letter_contact_block_be_changed_for_the_template(
    mock_get_service_letter_template,
    client_request,
    service_one,
    fake_uuid,
    contact_block_data,
    expected_partial_url,
    mock_get_page_counts_for_letter,
    mocker,
):
    mocker.patch("app.service_api_client.get_letter_contacts", return_value=contact_block_data)

    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert page.select_one("a.edit-template-link-letter-contact")["href"] == expected_partial_url(
        service_id=SERVICE_ONE_ID
    )


@pytest.mark.parametrize(
    "prefix_sms, expected_hint",
    [
        (True, "Your message will start with your service name"),
        (False, None),
    ],
)
@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_message_with_prefix_hint_if_enabled_for_service(
    client_request, mock_get_service_template, service_one, fake_uuid, prefix_sms, expected_hint
):
    service_one["prefix_sms"] = prefix_sms

    page = client_request.get(
        ".edit_service_template",
        service_id=service_one["id"],
        template_id=fake_uuid,
    )

    assert normalize_spaces(page.select_one(".govuk-hint#template_content-hint")) == expected_hint


@pytest.mark.parametrize("filetype", ["pdf", "png"])
@pytest.mark.parametrize(
    "view, extra_view_args",
    [
        ("no_cookie.view_letter_template_preview", {}),
        ("no_cookie.view_letter_template_preview", {"page": "2"}),
        ("no_cookie.view_letter_template_version_preview", {"version": 1}),
        ("no_cookie.view_letter_template_version_preview", {"version": 1, "page": "2"}),
    ],
)
def test_should_show_preview_letter_templates(
    view, extra_view_args, filetype, client_request, mock_get_service_email_template, service_one, fake_uuid, mocker
):
    mocked_preview = mocker.patch("app.template_preview_client.get_preview_for_templated_letter", return_value="foo")

    service_id, template_id = service_one["id"], fake_uuid

    response = client_request.get_response(
        view, service_id=service_id, template_id=template_id, filetype=filetype, **extra_view_args
    )

    assert response.get_data(as_text=True) == "foo"
    mock_get_service_email_template.assert_called_with(service_id, template_id, extra_view_args.get("version"))
    assert mocked_preview.call_args_list[0].kwargs["db_template"]["id"] == template_id
    assert mocked_preview.call_args_list[0].kwargs["db_template"]["service"] == service_id
    assert mocked_preview.call_args_list[0].kwargs["filetype"] == filetype
    assert mocked_preview.call_args_list[0].kwargs["service"].id == service_id

    if "page" in extra_view_args:
        assert mocked_preview.call_args[1]["page"] == extra_view_args["page"]
    else:
        assert mocked_preview.call_args[1]["page"] is None


def test_should_show_preview_letter_attachment(client_request, service_one, fake_uuid, mocker):
    mocked_preview = mocker.patch("app.template_preview_client.get_png_for_letter_attachment_page", return_value="foo")

    service_id, attachment_id = service_one["id"], fake_uuid

    response = client_request.get_response(
        "no_cookie.view_letter_attachment_preview",
        service_id=service_id,
        attachment_id=attachment_id,
    )

    assert response.get_data(as_text=True) == "foo"
    assert mocked_preview.call_args[0][0] == attachment_id
    assert mocked_preview.call_args[1]["service"].id == service_id


def test_dont_show_preview_letter_templates_for_bad_filetype(
    client_request, mock_get_service_template, service_one, fake_uuid
):
    client_request.get_response(
        "no_cookie.view_letter_template_preview",
        service_id=service_one["id"],
        template_id=fake_uuid,
        filetype="blah",
        _expected_status=404,
    )
    assert mock_get_service_template.called is False


def test_letter_branding_preview_image(
    client_request,
    mock_onwards_request_headers,
    mocker,
):
    class MockedResponse:
        content = "foo"
        status_code = 200
        headers = {}

    mocked_preview = mocker.patch("app.template_preview_client.requests_session.post", return_value=MockedResponse())
    response = client_request.get_response(
        "no_cookie.letter_branding_preview_image",
        filename="example",
    )

    mocked_preview.assert_called_with(
        "http://localhost:9999/preview.png",
        json={
            "letter_contact_block": "",
            "template": {
                "subject": "An example letter",
                "content": ANY,
                "template_type": "letter",
                "is_precompiled_letter": False,
            },
            "values": None,
            "filename": "example",
        },
        headers={
            "Authorization": "Token my-secret-key",
            "some-onwards": "request-headers",
        },
    )
    assert response.get_data(as_text=True) == "foo"


@pytest.mark.parametrize("filename", [None, FieldWithNoneOption.NONE_OPTION_VALUE])
@pytest.mark.parametrize("branding_style", [None, FieldWithNoneOption.NONE_OPTION_VALUE])
def test_letter_template_preview_handles_no_branding_style_or_filename_correctly(
    client_request,
    branding_style,
    filename,
    mocker,
):
    mocked_preview = mocker.patch("app.template_preview_client.get_preview_for_templated_letter")
    client_request.get_response(
        "no_cookie.letter_branding_preview_image",
        branding_style=branding_style,
        filename=filename,
    )
    mocked_preview.assert_called_once_with(ANY, branding_filename=None, filetype="png", service=ANY)


@pytest.mark.parametrize("filename", [None, FieldWithNoneOption.NONE_OPTION_VALUE])
def test_letter_template_preview_links_to_the_correct_image_when_passed_existing_branding(
    client_request,
    mock_get_letter_branding_by_id,
    filename,
    mocker,
):
    mocked_preview = mocker.patch("app.template_preview_client.get_preview_for_templated_letter")
    client_request.get_response(
        "no_cookie.letter_branding_preview_image",
        branding_style="12341234-1234-1234-1234-123412341234",
        filename=filename,
    )

    mock_get_letter_branding_by_id.assert_called_once_with("12341234-1234-1234-1234-123412341234")
    mocked_preview.assert_called_once_with(ANY, branding_filename="hm-government", filetype="png", service=ANY)


@pytest.mark.parametrize("branding_style", [None, FieldWithNoneOption.NONE_OPTION_VALUE])
def test_letter_template_preview_links_to_the_correct_image_when_passed_a_filename(
    client_request,
    branding_style,
    mocker,
):
    mocked_preview = mocker.patch("app.template_preview_client.get_preview_for_templated_letter")
    client_request.get_response(
        "no_cookie.letter_branding_preview_image",
        branding_style=branding_style,
        filename="foo.svg",
    )
    mocked_preview.assert_called_once_with(ANY, branding_filename="foo.svg", filetype="png", service=ANY)


def test_letter_template_preview_returns_400_if_both_branding_style_and_filename_provided(
    client_request,
):
    client_request.get(
        "no_cookie.letter_branding_preview_image",
        branding_style="some-branding",
        filename="some-filename",
        _test_page_title=False,
        _expected_status=400,
    )


def test_choosing_to_copy_redirects(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
):
    client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        _data={"operation": "add-new-template", "add_template_by_template_type": "copy-existing"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.choose_template_to_copy",
            service_id=SERVICE_ONE_ID,
        ),
    )


def test_choosing_to_copy_redirects_and_includes_folder_id(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
):
    mock_get_template_folders.return_value = [
        _folder("Parent folder", PARENT_FOLDER_ID),
    ]
    client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        template_folder_id=PARENT_FOLDER_ID,
        _data={"operation": "add-new-template", "add_template_by_template_type": "copy-existing"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.choose_template_to_copy",
            service_id=SERVICE_ONE_ID,
            to_folder_id=PARENT_FOLDER_ID,
        ),
    )


def test_choosing_letter_creates(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_create_service_template,
    fake_uuid,
):
    service_one["permissions"].append("letter")
    client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        _data={"operation": "add-new-template", "add_template_by_template_type": "letter"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.view_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )
    mock_create_service_template.assert_called_once_with(
        name="Untitled letter template",
        type_="letter",
        content="Body text",
        service_id=SERVICE_ONE_ID,
        subject="Heading",
        parent_folder_id=None,
    )


def test_choose_a_template_to_copy(
    client_request,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_no_api_keys,
    mock_get_just_services_for_user,
):
    page = client_request.get(
        "main.choose_template_to_copy",
        service_id=SERVICE_ONE_ID,
    )

    assert page.select(".folder-heading") == []

    expected = [
        "Folder Service 1 6 templates",
        "Folder Service 1 sms_template_one Text message template",
        "Folder Service 1 sms_template_two Text message template",
        "Folder Service 1 email_template_one Email template",
        "Folder Service 1 email_template_two Email template",
        "Folder Service 1 letter_template_one Letter template",
        "Folder Service 1 letter_template_two Letter template",
        "Folder Service 2 6 templates",
        "Folder Service 2 sms_template_one Text message template",
        "Folder Service 2 sms_template_two Text message template",
        "Folder Service 2 email_template_one Email template",
        "Folder Service 2 email_template_two Email template",
        "Folder Service 2 letter_template_one Letter template",
        "Folder Service 2 letter_template_two Letter template",
    ]
    actual = page.select(".template-list-item")

    assert len(actual) == len(expected)

    for actual, expected in zip(actual, expected, strict=True):  # noqa: B020
        assert normalize_spaces(actual.text) == expected

    links = page.select(".template-list-item a")
    assert links[0]["href"] == url_for(
        "main.choose_template_to_copy",
        service_id=SERVICE_ONE_ID,
        from_service=SERVICE_TWO_ID,
    )
    assert links[1]["href"] == url_for(
        "main.choose_template_to_copy",
        service_id=SERVICE_ONE_ID,
        from_service=SERVICE_TWO_ID,
    )
    assert links[2]["href"] == url_for(
        "main.copy_template",
        service_id=SERVICE_ONE_ID,
        template_id=TEMPLATE_ONE_ID,
        from_service=SERVICE_TWO_ID,
    )


def test_choose_a_template_to_copy_passes_through_folder_id(
    client_request,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_no_api_keys,
    mock_get_just_services_for_user,
):
    page = client_request.get(
        "main.choose_template_to_copy",
        service_id=SERVICE_ONE_ID,
        to_folder_id=PARENT_FOLDER_ID,
    )

    assert page.select(".folder-heading") == []

    expected = [
        "Folder Service 1 6 templates",
        "Folder Service 1 sms_template_one Text message template",
        "Folder Service 1 sms_template_two Text message template",
        "Folder Service 1 email_template_one Email template",
        "Folder Service 1 email_template_two Email template",
        "Folder Service 1 letter_template_one Letter template",
        "Folder Service 1 letter_template_two Letter template",
        "Folder Service 2 6 templates",
        "Folder Service 2 sms_template_one Text message template",
        "Folder Service 2 sms_template_two Text message template",
        "Folder Service 2 email_template_one Email template",
        "Folder Service 2 email_template_two Email template",
        "Folder Service 2 letter_template_one Letter template",
        "Folder Service 2 letter_template_two Letter template",
    ]
    actual = page.select(".template-list-item")

    assert len(actual) == len(expected)

    for actual, expected in zip(actual, expected, strict=True):  # noqa: B020
        assert normalize_spaces(actual.text) == expected

    links = page.select(".template-list-item a")
    assert links[0]["href"] == url_for(
        "main.choose_template_to_copy",
        service_id=SERVICE_ONE_ID,
        from_service=SERVICE_TWO_ID,
        to_folder_id=PARENT_FOLDER_ID,
    )
    assert links[1]["href"] == url_for(
        "main.choose_template_to_copy",
        service_id=SERVICE_ONE_ID,
        from_service=SERVICE_TWO_ID,
        to_folder_id=PARENT_FOLDER_ID,
    )
    assert links[2]["href"] == url_for(
        "main.copy_template",
        service_id=SERVICE_ONE_ID,
        template_id=TEMPLATE_ONE_ID,
        from_service=SERVICE_TWO_ID,
        to_folder_id=PARENT_FOLDER_ID,
    )


def test_choose_a_template_to_copy_when_user_has_one_service(
    client_request,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_no_api_keys,
    mock_get_empty_organisations_and_one_service_for_user,
):
    page = client_request.get(
        "main.choose_template_to_copy",
        service_id=SERVICE_ONE_ID,
    )

    assert page.select(".folder-heading") == []

    expected = [
        "sms_template_one Text message template",
        "sms_template_two Text message template",
        "email_template_one Email template",
        "email_template_two Email template",
        "letter_template_one Letter template",
        "letter_template_two Letter template",
    ]
    actual = page.select(".template-list-item")

    assert len(actual) == len(expected)

    for actual, expected in zip(actual, expected, strict=True):  # noqa: B020
        assert normalize_spaces(actual.text) == expected

    assert page.select(".template-list-item a")[0]["href"] == url_for(
        "main.copy_template",
        service_id=SERVICE_ONE_ID,
        template_id=TEMPLATE_ONE_ID,
        from_service=SERVICE_TWO_ID,
    )


def test_choose_a_template_to_copy_from_folder_within_service(
    client_request,
    mock_get_template_folders,
    mock_get_non_empty_organisations_and_services_for_user,
    mock_get_no_api_keys,
    mocker,
):
    mock_get_template_folders.return_value = [
        _folder("Parent folder", PARENT_FOLDER_ID),
        _folder("Child folder empty", CHILD_FOLDER_ID, parent=PARENT_FOLDER_ID),
        _folder("Child folder non-empty", FOLDER_TWO_ID, parent=PARENT_FOLDER_ID),
    ]
    mocker.patch(
        "app.service_api_client.get_service_templates",
        return_value={
            "data": [
                _template(
                    "sms",
                    "Should not appear in list (at service root)",
                ),
                _template(
                    "sms",
                    "Should appear in list (at same level)",
                    parent=PARENT_FOLDER_ID,
                ),
                _template(
                    "sms",
                    "Should appear in list (nested)",
                    parent=FOLDER_TWO_ID,
                    template_id=TEMPLATE_ONE_ID,
                ),
            ]
        },
    )
    page = client_request.get(
        "main.choose_template_to_copy",
        service_id=SERVICE_ONE_ID,
        from_service=SERVICE_ONE_ID,
        from_folder=PARENT_FOLDER_ID,
    )

    assert normalize_spaces(page.select_one(".folder-heading").text) == "Folder Parent folder"
    breadcrumb_links = page.select(".folder-heading-breadcrumb a")
    assert len(breadcrumb_links) == 1
    assert breadcrumb_links[0]["href"] == url_for(
        "main.choose_template_to_copy",
        service_id=SERVICE_ONE_ID,
        from_service=SERVICE_ONE_ID,
    )

    expected = [
        "Folder Child folder empty Empty",
        "Folder Child folder non-empty 1 template",
        "Folder Child folder non-empty Should appear in list (nested) Text message template",
        "Should appear in list (at same level) Text message template",
    ]
    actual = page.select(".template-list-item")

    assert len(actual) == len(expected)

    for actual, expected in zip(actual, expected, strict=True):  # noqa: B020
        assert normalize_spaces(actual.text) == expected

    links = page.select(".template-list-item a")
    assert links[0]["href"] == url_for(
        "main.choose_template_to_copy",
        service_id=SERVICE_ONE_ID,
        from_service=SERVICE_ONE_ID,
        from_folder=CHILD_FOLDER_ID,
    )
    assert links[1]["href"] == url_for(
        "main.choose_template_to_copy",
        service_id=SERVICE_ONE_ID,
        from_service=SERVICE_ONE_ID,
        from_folder=FOLDER_TWO_ID,
    )
    assert links[2]["href"] == url_for(
        "main.choose_template_to_copy",
        service_id=SERVICE_ONE_ID,
        from_folder=FOLDER_TWO_ID,
    )
    assert links[3]["href"] == url_for(
        "main.copy_template",
        service_id=SERVICE_ONE_ID,
        template_id=TEMPLATE_ONE_ID,
        from_service=SERVICE_ONE_ID,
    )


@pytest.mark.parametrize(
    "existing_template_names, expected_name",
    (
        (["Two week reminder"], "Two week reminder (copy)"),
        (["Two week reminder (copy)"], "Two week reminder (copy 2)"),
        (["Two week reminder", "Two week reminder (copy)"], "Two week reminder (copy 2)"),
        (["Two week reminder (copy 8)", "Two week reminder (copy 9)"], "Two week reminder (copy 10)"),
        (["Two week reminder (copy)", "Two week reminder (copy 9)"], "Two week reminder (copy 10)"),
        (["Two week reminder (copy)", "Two week reminder (copy 10)"], "Two week reminder (copy 2)"),
    ),
)
def test_copy_template_page_renders_preview(
    client_request,
    active_user_with_permission_to_two_services,
    multiple_sms_senders,
    mock_get_service_templates,
    mock_get_service_email_template,
    mock_get_non_empty_organisations_and_services_for_user,
    existing_template_names,
    expected_name,
    mocker,
):
    mock_get_service_templates.side_effect = lambda service_id: {
        "data": [
            {"name": existing_template_name, "template_type": "sms"}
            for existing_template_name in existing_template_names
        ]
    }
    client_request.login(active_user_with_permission_to_two_services)
    page = client_request.get(
        "main.copy_template",
        service_id=SERVICE_ONE_ID,
        template_id=TEMPLATE_ONE_ID,
        from_service=SERVICE_TWO_ID,
    )

    back_link = page.select_one(".govuk-back-link")
    assert back_link["href"] == url_for(
        "main.choose_template_to_copy",
        service_id=SERVICE_ONE_ID,
        from_service=SERVICE_TWO_ID,
    )

    assert page.select_one("form")["method"] == "post"

    assert page.select_one("input[id=name]")["value"] == expected_name
    assert page.select_one("div[class=email-message]") is not None  # template is rendered on page
    assert mock_get_service_email_template.call_args_list == [mocker.call(SERVICE_TWO_ID, TEMPLATE_ONE_ID, None)]


def test_copy_template_loads_template_from_within_subfolder(
    client_request,
    active_user_with_permission_to_two_services,
    mock_get_service_templates,
    multiple_sms_senders,
    mock_get_non_empty_organisations_and_services_for_user,
    mocker,
):
    template = template_json(service_id=SERVICE_TWO_ID, id_=TEMPLATE_ONE_ID, name="foo", folder=PARENT_FOLDER_ID)

    mock_get_service_template = mocker.patch(
        "app.service_api_client.get_service_template", return_value={"data": template}
    )
    mock_get_template_folder = mocker.patch(
        "app.template_folder_api_client.get_template_folder",
        return_value=_folder("Parent folder", PARENT_FOLDER_ID),
    )
    client_request.login(active_user_with_permission_to_two_services)

    page = client_request.get(
        "main.copy_template",
        service_id=SERVICE_ONE_ID,
        template_id=TEMPLATE_ONE_ID,
        from_service=SERVICE_TWO_ID,
    )

    back_link = page.select_one(".govuk-back-link")
    assert back_link["href"] == url_for(
        "main.choose_template_to_copy",
        service_id=SERVICE_ONE_ID,
        from_service=SERVICE_TWO_ID,
        from_folder=PARENT_FOLDER_ID,
    )

    assert page.select_one("input[id=name]")["value"] == "foo (copy)"
    assert mock_get_service_template.call_args_list == [mocker.call(SERVICE_TWO_ID, TEMPLATE_ONE_ID, None)]
    assert mock_get_template_folder.call_args_list == [mocker.call(SERVICE_TWO_ID, PARENT_FOLDER_ID)]


def test_copy_letter_template_across_service_boundary(
    client_request,
    active_user_with_permission_to_two_services,
    mock_get_service_templates,
    multiple_sms_senders,
    mocker,
):
    template = template_json(service_id=SERVICE_TWO_ID, id_=TEMPLATE_ONE_ID, name="foo", folder=None, type_="letter")
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": template})
    client_request.login(active_user_with_permission_to_two_services)
    request_mock_returns = Mock(
        content=b'{"count": 4, "welsh_page_count": 1, "attachment_page_count": 2}', status_code=200
    )
    mocker.patch("app.template_preview_client.requests_session.post", return_value=request_mock_returns)

    page = client_request.get(
        "main.copy_template",
        service_id=SERVICE_ONE_ID,
        template_id=TEMPLATE_ONE_ID,
        from_service=SERVICE_TWO_ID,
    )

    for img in page.select("img"):
        assert img.get("src").startswith(f"/services/{SERVICE_TWO_ID}/templates/{TEMPLATE_ONE_ID}.png")


def test_cant_copy_template_from_non_member_service(
    client_request,
    mock_get_service_email_template,
    mock_get_organisations_and_services_for_user,
):
    client_request.get(
        "main.copy_template",
        service_id=SERVICE_ONE_ID,
        template_id=TEMPLATE_ONE_ID,
        from_service=SERVICE_TWO_ID,
        _expected_status=403,
    )
    assert mock_get_service_email_template.call_args_list == []


def test_post_copy_template(
    client_request,
    active_user_with_permissions,
    mock_get_service,
    multiple_sms_senders,
    mock_get_service_email_template,
    mock_get_service_templates,
    mock_get_organisations_and_services_for_user,
    mock_create_service_template,
    mocker,
):
    active_user_with_permissions["services"].append(SERVICE_TWO_ID)
    active_user_with_permissions["permissions"][SERVICE_TWO_ID] = active_user_with_permissions["permissions"][
        SERVICE_ONE_ID
    ]
    client_request.post(
        "main.copy_template",
        service_id=SERVICE_ONE_ID,
        from_service=SERVICE_TWO_ID,
        template_id=TEMPLATE_ONE_ID,
        _data={
            "service": SERVICE_ONE_ID,
            "name": "Two week reminder (copy)",
        },
        _expected_status=302,
    )
    assert mock_create_service_template.call_args_list == [
        mocker.call(
            name="Two week reminder (copy)",
            type_="email",
            service_id=SERVICE_ONE_ID,
            parent_folder_id=None,
            subject="Your ((thing)) is due soon",
            content="Your vehicle tax expires on ((date))",
            letter_languages=None,
            letter_welsh_subject=None,
            letter_welsh_content=None,
            has_unsubscribe_link=None,
        )
    ]


def test_post_copy_template_into_folder(
    client_request,
    active_user_with_permissions,
    mock_get_service,
    multiple_sms_senders,
    mock_get_service_email_template,
    mock_get_service_templates,
    mock_get_organisations_and_services_for_user,
    mock_create_service_template,
    mocker,
):
    active_user_with_permissions["services"].append(SERVICE_TWO_ID)
    active_user_with_permissions["permissions"][SERVICE_TWO_ID] = active_user_with_permissions["permissions"][
        SERVICE_ONE_ID
    ]
    client_request.post(
        "main.copy_template",
        service_id=SERVICE_ONE_ID,
        from_service=SERVICE_TWO_ID,
        template_id=TEMPLATE_ONE_ID,
        to_folder_id=PARENT_FOLDER_ID,
        _data={
            "service": SERVICE_ONE_ID,
            "name": "Two week reminder (copy)",
        },
        _expected_status=302,
    )
    assert mock_create_service_template.call_args_list == [
        mocker.call(
            name="Two week reminder (copy)",
            type_="email",
            service_id=SERVICE_ONE_ID,
            subject="Your ((thing)) is due soon",
            content="Your vehicle tax expires on ((date))",
            parent_folder_id=PARENT_FOLDER_ID,
            letter_languages=None,
            letter_welsh_subject=None,
            letter_welsh_content=None,
            has_unsubscribe_link=None,
        )
    ]


def test_post_copy_letter_template(
    client_request,
    mock_get_service_letter_template,
    mock_get_service_templates,
    multiple_sms_senders,
    mock_get_organisations_and_services_for_user,
    mock_create_service_template,
    service_one,
    mocker,
):
    service_one["permissions"].append("letter")

    client_request.post(
        "main.copy_template",
        service_id=SERVICE_ONE_ID,
        from_service=SERVICE_ONE_ID,
        template_id=TEMPLATE_ONE_ID,
        _data={
            "service": SERVICE_ONE_ID,
            "name": "Two week reminder (copy)",
        },
        _expected_status=302,
    )
    assert mock_create_service_template.call_args_list == [
        mocker.call(
            name="Two week reminder (copy)",
            type_="letter",
            service_id=SERVICE_ONE_ID,
            subject="Subject",
            parent_folder_id=None,
            content="Template <em>content</em> with & entity",
            letter_languages="english",
            letter_welsh_subject=None,
            letter_welsh_content=None,
            has_unsubscribe_link=None,
        )
    ]


@pytest.mark.parametrize("from_service", (SERVICE_ONE_ID, SERVICE_TWO_ID))
def test_copy_letter_template_with_letter_attachment(
    client_request,
    active_user_with_permission_to_two_services,
    mock_get_service_templates,
    mock_get_service_letter_template_with_attachment,
    mock_create_service_template,
    multiple_sms_senders,
    from_service,
    mocker,
):
    client_request.login(active_user_with_permission_to_two_services)
    mocker.patch(
        "app.main.views_nl.templates.s3download",
        return_value=BytesIO(b"PDF"),
    )
    mock_upload = mocker.patch("app.main.views_nl.templates.upload_letter_attachment_to_s3")
    mock_save_to_db = mocker.patch("app.letter_attachment_client.create_letter_attachment")
    mocker.patch("uuid.uuid4", return_value="12341234-1234-1234-1234-123412341234")

    client_request.post(
        "main.copy_template",
        service_id=SERVICE_ONE_ID,
        from_service=from_service,
        template_id=TEMPLATE_ONE_ID,
        _data={
            "service": SERVICE_ONE_ID,
            "name": "Two week reminder (copy)",
        },
        _expected_status=302,
    )
    assert mock_create_service_template.call_args_list == [
        mocker.call(
            name="Two week reminder (copy)",
            type_="letter",
            service_id=SERVICE_ONE_ID,
            subject="Subject",
            parent_folder_id=None,
            content="Template <em>content</em> with & entity",
            letter_languages="english",
            letter_welsh_subject=None,
            letter_welsh_content=None,
            has_unsubscribe_link=None,
        )
    ]
    assert mock_upload.call_args_list == [
        mocker.call(
            b"PDF",
            file_location=f"service-{SERVICE_ONE_ID}/12341234-1234-1234-1234-123412341234.pdf",
            page_count=1,
            original_filename="original file.pdf",
        )
    ]
    assert mock_save_to_db.call_args_list == [
        mocker.call(
            upload_id="12341234-1234-1234-1234-123412341234",
            original_filename="original file.pdf",
            page_count=1,
            template_id=mocker.ANY,
            service_id=SERVICE_ONE_ID,
        )
    ]


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "template_type, expected_page_heading",
    [
        ("email", "New email template"),
        ("sms", "New text message template"),
        ("letter", "Templates"),
    ],
)
def test_choose_template_for_each_template_type(
    client_request,
    mock_get_api_keys,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    template_type,
    expected_page_heading,
):
    service_one["permissions"].append("letter")

    page = client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        _data={
            "operation": "add-new-template",
            "add_template_by_template_type": template_type,
        },
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one("h1").text) == expected_page_heading


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "service_permissions, data, expected_error",
    (
        (
            ["letter"],
            {
                "operation": "add-new-template",
                "add_template_by_template_type": "email",
            },
            "Sending emails has been disabled for your service.",
        ),
        (
            ["email"],
            {
                "operation": "add-new-template",
                "add_template_by_template_type": "sms",
            },
            "Sending text messages has been disabled for your service.",
        ),
        (
            ["sms"],
            {
                "operation": "add-new-template",
                "add_template_by_template_type": "letter",
            },
            "Sending letters has been disabled for your service.",
        ),
    ),
)
def test_should_not_allow_creation_of_template_through_form_without_correct_permission(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    service_permissions,
    data,
    expected_error,
):
    service_one["permissions"] = service_permissions
    page = client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        _data=data,
        _follow_redirects=True,
        _expected_status=403,
    )
    assert normalize_spaces(page.select("main p")[0].text) == expected_error
    assert page.select_one(".govuk-back-link").text.strip() == "Back"
    assert page.select(".govuk-back-link")[0]["href"] == url_for(
        ".choose_template",
        service_id=SERVICE_ONE_ID,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize("method", ("get", "post"))
@pytest.mark.parametrize(
    "type_of_template, expected_status, expected_error",
    [
        ("email", 403, "Sending emails has been disabled for your service."),
        ("sms", 403, "Sending text messages has been disabled for your service."),
        ("foo", 404, None),
    ],
)
def test_should_not_allow_creation_of_a_template_without_correct_permission(
    client_request,
    service_one,
    method,
    type_of_template,
    expected_status,
    expected_error,
):
    service_one["permissions"] = []

    page = getattr(client_request, method)(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type=type_of_template,
        _follow_redirects=True,
        _expected_status=expected_status,
    )
    if expected_error:
        assert page.select("main p")[0].text.strip() == expected_error
        assert page.select_one(".govuk-back-link").text.strip() == "Back"
        assert page.select(".govuk-back-link")[0]["href"] == url_for(
            ".choose_template",
            service_id=service_one["id"],
        )


@pytest.mark.parametrize(
    "template_type,  expected_status_code",
    [
        ("email", 200),
        ("sms", 200),
        ("letter", 302),
    ],
)
def test_should_redirect_to_one_off_if_template_type_is_letter(
    client_request,
    multiple_reply_to_email_addresses,
    multiple_sms_senders,
    fake_uuid,
    mocker,
    template_type,
    expected_status_code,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={"data": create_template(template_type=template_type)},
    )
    client_request.get(
        ".set_sender",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=expected_status_code,
        _expected_redirect=(
            None
            if expected_status_code == 200
            else url_for(
                "main.send_one_off",
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            )
        ),
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_page_to_rename_template(
    client_request,
    mock_get_service_letter_template,
    fake_uuid,
):
    page = client_request.get(
        ".rename_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Rename template"
    form = page.select_one("form[method=post]")
    assert "action" not in form

    assert form.select_one("input[name=name]")
    assert normalize_spaces(form.select_one("label[for=name]").text) == "Template name"


def test_should_show_rename_template(
    client_request,
    mock_get_service_letter_template,
    mock_update_service_template,
    fake_uuid,
):
    client_request.post(
        ".rename_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "name": "new name",
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.view_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )
    mock_update_service_template.assert_called_with(
        template_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        name="new name",
    )


def test_name_required_to_rename_template(
    client_request,
    mock_get_service_letter_template,
    fake_uuid,
):
    page = client_request.post(
        ".rename_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "name": "",
        },
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: Enter Template name"


@pytest.mark.parametrize("template_type", ("email", "sms"))
def test_only_letters_can_be_renamed_through_rename_page(
    client_request,
    fake_uuid,
    template_type,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={"data": create_template(template_type=template_type)},
    )

    client_request.post(
        ".rename_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "name": "",
        },
        _expected_status=404,
    )


@pytest.mark.parametrize(
    "service_id, template_id",
    (
        (
            SERVICE_ONE_ID,
            sample_uuid(),
        ),
        (
            SERVICE_ONE_ID.upper(),
            sample_uuid().upper(),
        ),
    ),
)
def test_should_redirect_when_saving_a_template(
    client_request,
    mock_get_service_template,
    mock_get_api_keys,
    mock_update_service_template,
    service_id,
    template_id,
):
    name = "new name"
    content = "template <em>content</em> with & entity"
    client_request.post(
        ".edit_service_template",
        service_id=service_id,
        template_id=template_id,
        _data={
            "id": template_id,
            "name": name,
            "template_content": content,
            "template_type": "sms",
            "service": service_id,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.view_template",
            # UUIDs are always lowercase here
            service_id=SERVICE_ONE_ID,
            template_id=sample_uuid(),
        ),
    )
    mock_update_service_template.assert_called_with(
        # UUIDs are always lowercase here
        template_id=sample_uuid(),
        service_id=SERVICE_ONE_ID,
        name=name,
        content=content,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_not_allow_template_edits_without_correct_permission(
    client_request,
    mock_get_service_template,
    service_one,
    fake_uuid,
):
    service_one["permissions"] = ["email"]

    page = client_request.get(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _follow_redirects=True,
        _expected_status=403,
    )

    assert page.select("main p")[0].text.strip() == "Sending text messages has been disabled for your service."
    assert page.select_one(".govuk-back-link").text.strip() == "Back"
    assert page.select(".govuk-back-link")[0]["href"] == url_for(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "old_content, new_content, expected_paragraphs",
    [
        (
            "my favourite colour is blue",
            "my favourite colour is ((colour))",
            [
                "You added ((colour))",
                "Before you send any messages, make sure your API calls include colour.",
            ],
        ),
        (
            "hello ((name))",
            "hello ((first name)) ((middle name)) ((last name))",
            [
                "You removed ((name))",
                "You added ((first name)) ((middle name)) and ((last name))",
                "Before you send any messages, make sure your API calls include first name, middle name and last name.",
            ],
        ),
    ],
)
def test_should_show_interstitial_when_making_breaking_change_to_sms_template(
    client_request,
    service_one,
    mock_update_service_template,
    mock_get_api_keys,
    fake_uuid,
    mocker,
    new_content,
    old_content,
    expected_paragraphs,
):
    service_one["permissions"] += ["sms"]

    email_template = create_template(
        template_id=fake_uuid, template_type="sms", name="my old name", content=old_content
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})

    data = {
        "id": fake_uuid,
        "name": "my new template name",
        "template_content": new_content,
        "template_type": "sms",
        "service": SERVICE_ONE_ID,
    }

    page = client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data=data,
        _expected_status=200,
    )

    assert page.select_one("h1").string.strip() == "Confirm changes"
    assert page.select_one("a.govuk-back-link")["href"] == url_for(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )
    assert [normalize_spaces(paragraph.text) for paragraph in page.select("main p")] == expected_paragraphs

    for key, value in (
        {
            "name": "my new template name",
            "template_content": new_content,
            "confirm": "true",
        }
    ).items():
        assert page.select_one(f"input[name={key}]")["value"] == value


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "template_type, additional_data",
    (
        ("email", {"name": "new name"}),
        ("letter", {}),
    ),
)
@pytest.mark.parametrize(
    "old_content, new_content, expected_paragraphs",
    [
        (
            "my favourite colour is blue",
            "my favourite colour is ((colour))",
            [
                "You added ((colour))",
                "Before you send any messages, make sure your API calls include colour.",
            ],
        ),
        (
            "hello ((name))",
            "hello ((first name)) ((middle name)) ((last name))",
            [
                "You removed ((name))",
                "You added ((first name)) ((middle name)) and ((last name))",
                "Before you send any messages, make sure your API calls include first name, middle name and last name.",
            ],
        ),
    ],
)
def test_should_show_interstitial_when_making_breaking_change(
    client_request,
    service_one,
    mock_get_api_keys,
    fake_uuid,
    mocker,
    new_content,
    old_content,
    expected_paragraphs,
    template_type,
    additional_data,
):
    service_one["permissions"] += [template_type]

    email_template = create_template(
        template_id=fake_uuid, template_type=template_type, subject="Your ((thing)) is due soon", content=old_content
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})

    data = {
        "id": fake_uuid,
        "template_content": new_content,
        "template_type": "email",
        "subject": "reminder '\" <span> & ((thing))",
        "service": SERVICE_ONE_ID,
    } | additional_data

    page = client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data=data,
        _expected_status=200,
    )

    assert page.select_one("h1").string.strip() == "Confirm changes"
    assert page.select_one("a.govuk-back-link")["href"] == url_for(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )
    assert [normalize_spaces(paragraph.text) for paragraph in page.select("main p")] == expected_paragraphs

    for key, value in (
        {
            "subject": "reminder '\" <span> & ((thing))",
            "template_content": new_content,
            "confirm": "true",
        }
        | additional_data
    ).items():
        assert page.select_one(f"input[name={key}]")["value"] == value

    # BeautifulSoup returns the value attribute as unencoded, let’s make
    # sure that it is properly encoded in the HTML
    assert str(page.select_one("input[name=subject]")) == (
        """<input name="subject" type="hidden" value="reminder '&quot; &lt;span&gt; &amp; ((thing))"/>"""
    )


@pytest.mark.parametrize(
    "url_kwargs",
    [
        {},
        {"language": "welsh"},
    ],
)
def test_confirm_breaking_change_on_letter_template_saves_correct_language_content(
    client_request,
    service_one,
    mock_update_service_template,
    mock_get_api_keys,
    fake_uuid,
    mocker,
    url_kwargs,
):
    service_one["permissions"].append("letter")

    letter_template = template_json(
        id_=fake_uuid,
        service_id=SERVICE_ONE_ID,
        type_="letter",
        name="a letter template",
        subject="old english subject",
        content="old english content",
        letter_languages="welsh_then_english",
        letter_welsh_subject="old welsh subject",
        letter_welsh_content="old welsh content",
        redact_personalisation=False,
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": letter_template})
    do_mock_get_page_counts_for_letter(mocker, count=2)
    mocker.patch("app.service_api_client.get_letter_contacts", return_value=[create_letter_contact_block()])

    data = {
        "id": fake_uuid,
        "subject": "updated subject ((new_var))",
        "template_content": "updated content ((new_var2))",
        "service": SERVICE_ONE_ID,
        "confirm": True,
    }

    client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        **url_kwargs,
        _data=data,
        _follow_redirects=True,
    )

    if url_kwargs:
        assert mock_update_service_template.call_args_list == [
            mocker.call(
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
                name="a letter template",
                letter_welsh_subject="updated subject ((new_var))",
                letter_welsh_content="updated content ((new_var2))",
            )
        ]
    else:
        assert mock_update_service_template.call_args_list == [
            mocker.call(
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
                name="a letter template",
                subject="updated subject ((new_var))",
                content="updated content ((new_var2))",
            )
        ]


def test_removing_placeholders_is_not_a_breaking_change(
    client_request,
    mock_get_service_email_template,
    mock_update_service_template,
    fake_uuid,
):
    existing_template = mock_get_service_email_template(0, 0)["data"]
    client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "name": existing_template["name"],
            "template_content": "no placeholders",
            "subject": existing_template["subject"],
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.view_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )
    assert mock_update_service_template.called is True


def test_should_not_create_too_big_template(
    client_request,
    mock_create_service_template_content_too_big,
):
    page = client_request.post(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type="sms",
        _data={
            "name": "new name",
            "template_content": "template content",
            "template_type": "sms",
            "service": SERVICE_ONE_ID,
        },
        _expected_status=200,
    )
    assert "Content has a character count greater than the limit of 459" in page.text


def test_should_not_update_too_big_template(
    client_request,
    mock_get_service_template,
    mock_update_service_template_400_content_too_big,
    fake_uuid,
):
    page = client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "id": fake_uuid,
            "name": "new name",
            "template_content": "template content",
            "service": SERVICE_ONE_ID,
            "template_type": "sms",
        },
        _expected_status=200,
    )
    assert "Content has a character count greater than the limit of 459" in page.text


def test_should_not_edit_letter_template_with_too_big_qr_code(
    client_request,
    mock_get_service_template,
    mock_update_service_template_400_qr_code_too_big,
    fake_uuid,
    service_one,
):
    service_one["permissions"].append("letter")

    page = client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "name": "new name",
            "subject": "subject",
            "template_content": "qr: " + ("content" * 100),
            "template_type": "letter",
            "service": SERVICE_ONE_ID,
        },
        _expected_status=200,
    )
    assert (
        normalize_spaces(page.select_one(".govuk-error-message").text)
        == "Error: Cannot create a usable QR code - the link you entered is too long"
    )


def test_should_redirect_when_saving_a_template_email(
    client_request,
    mock_get_service_email_template,
    mock_update_service_template,
    fake_uuid,
):
    name = "new name"
    content = "template <em>content</em> with & entity ((thing)) ((date))"
    subject = "subject & entity"
    client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "id": fake_uuid,
            "name": name,
            "template_content": content,
            "template_type": "email",
            "service": SERVICE_ONE_ID,
            "subject": subject,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.view_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )
    mock_update_service_template.assert_called_with(
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        name=name,
        content=content,
        subject=subject,
        has_unsubscribe_link=False,
    )


def test_should_redirect_when_saving_a_template_letter(
    client_request,
    mock_get_service_letter_template,
    mock_get_page_counts_for_letter,
    mock_update_service_template,
    fake_uuid,
    service_one,
):
    service_one["permissions"].append("letter")
    name = "new template name"
    content = "new letter content"
    subject = "new letter subject"
    client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "name": name,
            "subject": subject,
            "template_content": content,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.view_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )
    mock_update_service_template.assert_called_with(
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        name=name,
        content=content,
        subject=subject,
    )


@pytest.mark.parametrize(
    "language, mock_fixturename",
    (
        pytest.param(
            "welsh",
            "mock_get_service_letter_template",
            marks=pytest.mark.xfail(
                raises=AssertionError,
                reason="Cannot edit Welsh language content on template with letter_languages=english",
            ),
        ),
        pytest.param(
            "welsh",
            "mock_get_service_letter_template",
            marks=pytest.mark.xfail(
                raises=AssertionError,
                reason="Cannot edit Welsh language content on template with letter_languages=english",
            ),
        ),
        pytest.param(
            "gaelic",
            "mock_get_service_letter_template_welsh_language",
            marks=pytest.mark.xfail(
                raises=AssertionError,
                reason="The only accepted explicit language for editing letter templates is Welsh",
            ),
        ),
        (
            "welsh",
            "mock_get_service_letter_template_welsh_language",
        ),
    ),
)
def test_update_template_for_welsh_language_content(
    request,
    client_request,
    mock_update_service_template,
    mock_get_page_counts_for_letter,
    fake_uuid,
    service_one,
    language,
    mock_fixturename,
):
    # Load get_service_letter_template fixture
    request.getfixturevalue(mock_fixturename)

    service_one["permissions"].append("letter")
    name = "new template name"
    content = "Welsh letter content"
    subject = "Welsh letter subject"
    client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        language=language,
        _data={
            "name": name,
            "subject": subject,
            "template_content": content,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.view_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )
    mock_update_service_template.assert_called_with(
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        name=name,
        letter_welsh_subject=subject,
        letter_welsh_content=content,
    )


def test_update_template_for_english_content_in_welsh_letter(
    client_request,
    mock_update_service_template,
    mock_get_service_letter_template_welsh_language,
    fake_uuid,
    service_one,
    mocker,
):
    do_mock_get_page_counts_for_letter(mocker, count=1, welsh_page_count=1)
    service_one["permissions"].append("letter")
    name = "new template name"
    content = "English letter content"
    subject = "English letter subject"
    client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "name": name,
            "subject": subject,
            "template_content": content,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.view_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _anchor="first-page-of-english-in-bilingual-letter",
        ),
    )
    mock_update_service_template.assert_called_with(
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        name=name,
        subject=subject,
        content=content,
    )


@pytest.mark.parametrize("mock_fixturename", ["mock_get_service_email_template", "mock_get_service_template"])
def test_cannot_edit_welsh_content_for_email_or_sms_templates(
    request,
    client_request,
    mock_fixturename,
    mock_update_service_template,
    fake_uuid,
):
    # Load fixture to mock get email/sms template
    request.getfixturevalue(mock_fixturename)

    name = "new name"
    content = "new content"
    subject = "new subject"
    client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        language="welsh",
        _data={
            "name": name,
            "template_content": content,
            "subject": subject,
        },
        _expected_status=404,
    )


def test_should_show_delete_template_page_with_time_block(
    client_request, mock_get_service_template, mock_get_template_folders, mocker, fake_uuid
):
    mocker.patch("app.template_statistics_client.get_last_used_date_for_template", return_value="2012-01-01 12:00:00")

    with freeze_time("2012-01-01 12:10:00"):
        page = client_request.get(
            ".delete_service_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _test_page_title=False,
        )
    assert "Are you sure you want to delete ‘Two week reminder’?" in page.select(".banner-dangerous")[0].text
    assert normalize_spaces(page.select(".banner-dangerous p")[0].text) == (
        "This template was last used 10 minutes ago."
    )
    assert normalize_spaces(page.select(".sms-message-wrapper")[0].text) == (
        "service one: Template <em>content</em> with & entity"
    )
    mock_get_service_template.assert_called_with(SERVICE_ONE_ID, fake_uuid, None)


def test_should_show_delete_template_page_with_time_block_for_empty_notification(
    client_request, mock_get_service_template, mock_get_template_folders, mocker, fake_uuid
):
    mocker.patch("app.template_statistics_client.get_last_used_date_for_template", return_value=None)

    with freeze_time("2012-01-01 11:00:00"):
        page = client_request.get(
            ".delete_service_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _test_page_title=False,
        )

    expected_confirmation_question = "Are you sure you want to delete ‘Two week reminder’?"
    expected_usage_hint = "This template has not been used within the last year."
    expected_template_content = "service one: Template <em>content</em> with & entity"

    assert expected_confirmation_question in page.select(".banner-dangerous")[0].text
    assert normalize_spaces(page.select(".banner-dangerous p")[0].text) == expected_usage_hint
    assert normalize_spaces(page.select(".sms-message-wrapper")[0].text) == expected_template_content

    mock_get_service_template.assert_called_with(SERVICE_ONE_ID, fake_uuid, None)


def test_should_show_delete_template_page_with_never_used_block(
    client_request,
    mock_get_service_template,
    mock_get_template_folders,
    fake_uuid,
    mocker,
):
    mocker.patch(
        "app.template_statistics_client.get_last_used_date_for_template",
        side_effect=HTTPError(response=Mock(status_code=404), message="Default message"),
    )
    page = client_request.get(
        ".delete_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )
    assert "Are you sure you want to delete ‘Two week reminder’?" in page.select(".banner-dangerous")[0].text
    assert not page.select(".banner-dangerous p")
    assert normalize_spaces(page.select(".sms-message-wrapper")[0].text) == (
        "service one: Template <em>content</em> with & entity"
    )
    mock_get_service_template.assert_called_with(SERVICE_ONE_ID, fake_uuid, None)


def test_should_show_delete_template_page_with_escaped_template_name(client_request, mocker, fake_uuid):
    template = template_json(service_id=SERVICE_ONE_ID, id_=fake_uuid, name="<script>evil</script>")

    mocker.patch("app.template_statistics_client.get_last_used_date_for_template", return_value=None)
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": template})

    page = client_request.get(
        ".delete_service_template", service_id=SERVICE_ONE_ID, template_id=fake_uuid, _test_page_title=False
    )
    banner = page.select_one(".banner-dangerous")
    assert banner.select("script") == []


@pytest.mark.parametrize("parent", (PARENT_FOLDER_ID, None))
def test_should_redirect_when_deleting_a_template(
    client_request,
    mock_delete_service_template,
    mock_get_template_folders,
    parent,
    mocker,
):
    mock_get_template_folders.return_value = [
        {"id": PARENT_FOLDER_ID, "name": "Folder", "parent": None, "users_with_permission": [ANY]}
    ]
    mock_get_service_template = mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": _template(
                "sms",
                "Hello",
                parent=parent,
            )
        },
    )

    client_request.post(
        ".delete_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=TEMPLATE_ONE_ID,
        _expected_status=302,
        _expected_redirect=url_for(
            ".choose_template",
            service_id=SERVICE_ONE_ID,
            template_folder_id=parent,
        ),
    )

    mock_get_service_template.assert_called_with(SERVICE_ONE_ID, TEMPLATE_ONE_ID, None)
    mock_delete_service_template.assert_called_with(SERVICE_ONE_ID, TEMPLATE_ONE_ID)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2016-01-01T15:00")
def test_should_show_page_for_a_deleted_template(
    client_request,
    mock_get_template_folders,
    mock_get_deleted_template,
    fake_uuid,
):
    template_id = fake_uuid
    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=template_id,
        _test_page_title=False,
    )

    content = str(page)
    assert url_for("main.edit_service_template", service_id=SERVICE_ONE_ID, template_id=fake_uuid) not in content
    assert url_for("main.send_one_off", service_id=SERVICE_ONE_ID, template_id=fake_uuid) not in content
    assert page.select("p.hint")[0].text.strip() == "This template was deleted today at 3:00pm."
    assert "Delete this template" not in page.select_one("main").text

    mock_get_deleted_template.assert_called_with(SERVICE_ONE_ID, template_id, None)


@pytest.mark.parametrize(
    "route", ["main.add_service_template", "main.edit_service_template", "main.delete_service_template"]
)
def test_route_permissions(
    route,
    notify_admin,
    client_request,
    api_user_active,
    service_one,
    mock_get_service_template,
    mock_get_template_folders,
    fake_uuid,
    mocker,
):
    mocker.patch("app.template_statistics_client.get_last_used_date_for_template", return_value="2012-01-01 12:00:00")
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        200,
        url_for(route, service_id=service_one["id"], template_type="sms", template_id=fake_uuid),
        ["manage_templates"],
        api_user_active,
        service_one,
    )


def test_route_permissions_for_choose_template(
    notify_admin,
    client_request,
    api_user_active,
    mock_get_template_folders,
    service_one,
    mock_get_service_templates,
    mock_get_no_api_keys,
    mocker,
):
    mocker.patch("app.job_api_client.get_job")
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        200,
        url_for(
            "main.choose_template",
            service_id=service_one["id"],
        ),
        [],
        api_user_active,
        service_one,
    )


@pytest.mark.parametrize(
    "route", ["main.add_service_template", "main.edit_service_template", "main.delete_service_template"]
)
def test_route_invalid_permissions(
    route,
    notify_admin,
    client_request,
    api_user_active,
    service_one,
    mock_get_service_template,
    fake_uuid,
    mocker,
):
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        403,
        url_for(route, service_id=service_one["id"], template_type="sms", template_id=fake_uuid),
        ["view_activity"],
        api_user_active,
        service_one,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "template_type, expected",
    (
        ("email", "New email template"),
        ("sms", "New text message template"),
    ),
)
def test_add_template_page_furniture(
    client_request,
    service_one,
    template_type,
    expected,
):
    service_one["permissions"] += [template_type]
    page = client_request.get(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type=template_type,
    )
    assert normalize_spaces(page.select_one("h1").text) == expected

    back_link = page.select_one(".govuk-back-link")
    assert back_link["href"] == url_for("main.choose_template", service_id=SERVICE_ONE_ID, template_folder_id=None)


def test_can_create_email_template_with_emoji(client_request, mock_create_service_template):
    client_request.post(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type="email",
        _data={
            "name": "new name",
            "subject": "Food incoming!",
            "template_content": "here's a burrito 🌯",
            "template_type": "email",
            "service": SERVICE_ONE_ID,
        },
        _expected_status=302,
    )
    assert mock_create_service_template.called is True


def test_should_not_create_sms_template_with_emoji(
    client_request,
    service_one,
    mock_create_service_template,
):
    page = client_request.post(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type="sms",
        _data={
            "name": "new name",
            "template_content": "here are some noodles 🍜",
            "template_type": "sms",
            "service": SERVICE_ONE_ID,
        },
        _expected_status=200,
    )
    assert "You cannot use 🍜 in text messages." in page.text
    assert mock_create_service_template.called is False


def test_should_not_update_sms_template_with_emoji(
    client_request,
    service_one,
    mock_update_service_template,
    fake_uuid,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": template_json(
                service_id=SERVICE_ONE_ID,
                id_=fake_uuid,
                type_="sms",
            )
        },
    )
    page = client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "id": fake_uuid,
            "name": "new name",
            "template_content": "here's a burger 🍔",
            "service": SERVICE_ONE_ID,
            "template_type": "sms",
        },
        _expected_status=200,
    )
    assert "You cannot use 🍔 in text messages." in page.text
    assert mock_update_service_template.called is False


def test_should_create_sms_template_without_downgrading_unicode_characters(
    client_request,
    service_one,
    mock_create_service_template,
):
    msg = "here:\tare some “fancy quotes” and non\u200bbreaking\u200bspaces"

    client_request.post(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type="sms",
        _data={
            "name": "new name",
            "template_content": msg,
            "template_type": "sms",
            "service": SERVICE_ONE_ID,
        },
        expected_status=302,
    )

    mock_create_service_template.assert_called_with(
        name=ANY,
        type_=ANY,
        content=msg,
        service_id=ANY,
        subject=ANY,
        parent_folder_id=ANY,
        has_unsubscribe_link=ANY,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_message_before_redacting_template(
    client_request,
    mock_get_service_template,
    service_one,
    fake_uuid,
):
    page = client_request.get(
        "main.redact_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert "Are you sure you want to hide personalisation after sending?" in page.select(".banner-dangerous")[0].text

    form = page.select(".banner-dangerous form")[0]

    assert "action" not in form
    assert form["method"] == "post"


def test_should_show_redact_template(
    client_request,
    mock_get_service_template,
    mock_redact_template,
    service_one,
    fake_uuid,
):
    page = client_request.post(
        "main.redact_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select(".banner-default-with-tick")[0].text) == (
        "Personalised content will be hidden for messages sent with this template"
    )

    mock_redact_template.assert_called_once_with(SERVICE_ONE_ID, fake_uuid)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_hint_once_template_redacted(
    client_request,
    mocker,
    service_one,
    fake_uuid,
):
    template = create_template(template_type="email", content="hi ((name))", redact_personalisation=True)
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": template})

    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert page.select(".hint")[0].text == "Personalisation is hidden after sending"


def test_should_not_show_redaction_stuff_for_letters(
    client_request,
    fake_uuid,
    mock_get_service_letter_template,
    single_letter_contact_block,
    mock_get_page_counts_for_letter,
):
    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert page.select(".hint") == []
    assert "personalisation" not in " ".join(link.text.lower() for link in page.select("a"))


def test_set_template_sender(
    client_request,
    fake_uuid,
    mock_update_service_template_sender,
    mock_get_service_letter_template,
    single_letter_contact_block,
):
    data = {
        "sender": "1234",
    }

    client_request.post(
        "main.set_template_sender",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data=data,
    )

    mock_update_service_template_sender.assert_called_once_with(
        SERVICE_ONE_ID,
        fake_uuid,
        "1234",
    )


@pytest.mark.parametrize(
    "contact_block_data",
    [
        [],  # no letter contact blocks
        [create_letter_contact_block()],
    ],
)
def test_add_sender_link_only_appears_on_services_with_no_senders(
    client_request,
    fake_uuid,
    mocker,
    contact_block_data,
    mock_get_service_letter_template,
):
    mocker.patch("app.service_api_client.get_letter_contacts", return_value=contact_block_data)
    page = client_request.get(
        "main.set_template_sender",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    assert page.select_one("form .page-footer + a")["href"] == url_for(
        "main.service_add_letter_contact",
        service_id=SERVICE_ONE_ID,
        from_template=fake_uuid,
    )


def test_set_template_sender_escapes_letter_contact_block_names(
    client_request,
    fake_uuid,
    mocker,
    mock_get_service_letter_template,
):
    letter_contact_block = create_letter_contact_block(contact_block="foo\n\n<script>\n\nbar")
    mocker.patch("app.service_api_client.get_letter_contacts", return_value=[letter_contact_block])
    page = client_request.get(
        "main.set_template_sender",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    # use decode_contents, which returns the raw html, rather than text, which sanitises it and makes
    # testing confusing
    radio_text = page.select_one('.govuk-grid-column-three-quarters label[for="sender-1"]').decode_contents()
    assert "&lt;script&gt;" in radio_text
    assert "<script>" not in radio_text


@pytest.mark.parametrize(
    "prefix_sms, content, expected_message, expected_class",
    (
        (
            False,
            "",
            "Will be charged as 1 text message",
            None,
        ),
        (
            False,
            "a" * 160,
            "Will be charged as 1 text message",
            None,
        ),
        (
            False,
            "a" * 161,
            "Will be charged as 2 text messages",
            None,
        ),
        (
            # service name takes 13 characters, 147 + 13 = 160
            True,
            "a" * 147,
            "Will be charged as 1 text message",
            None,
        ),
        (
            # service name takes 13 characters, 148 + 13 = 161
            True,
            "a" * 148,
            "Will be charged as 2 text messages",
            None,
        ),
        (
            False,
            "a" * 918,
            "Will be charged as 6 text messages",
            None,
        ),
        (
            # Service name increases fragment count but doesn’t count
            # against total character limit
            True,
            "a" * 918,
            "Will be charged as 7 text messages",
            None,
        ),
        (
            # Can’t make a 7 fragment text template from content alone
            False,
            "a" * 919,
            "You have 1 character too many",
            "govuk-error-message",
        ),
        (
            # Service name increases content count but character count
            # is based on content alone
            True,
            "a" * 919,
            "You have 1 character too many",
            "govuk-error-message",
        ),
        (
            # Service name increases content count but character count
            # is based on content alone
            True,
            "a" * 920,
            "You have 2 characters too many",
            "govuk-error-message",
        ),
        (
            False,
            "Ẅ" * 70,
            "Will be charged as 1 text message",
            None,
        ),
        (
            False,
            "Ẅ" * 71,
            "Will be charged as 2 text messages",
            None,
        ),
        (
            False,
            "Ẅ" * 918,
            "Will be charged as 14 text messages",
            None,
        ),
        (
            False,
            "Ẅ" * 919,
            "You have 1 character too many",
            "govuk-error-message",
        ),
        (
            False,
            "Hello ((name))",
            "Will be charged as 1 text message (not including personalisation)",
            None,
        ),
        (
            # Length of placeholder body doesn’t count towards fragment count
            False,
            f"Hello (( {'a' * 999} ))",
            "Will be charged as 1 text message (not including personalisation)",
            None,
        ),
    ),
)
def test_content_count_json_endpoint(
    client_request,
    service_one,
    prefix_sms,
    content,
    expected_message,
    expected_class,
):
    service_one["prefix_sms"] = prefix_sms
    response = client_request.post_response(
        "main.count_content_length",
        service_id=SERVICE_ONE_ID,
        template_type="sms",
        _data={
            "template_content": content,
        },
        _expected_status=200,
    )

    html = json.loads(response.get_data(as_text=True))["html"]
    snippet = NotifyBeautifulSoup(html, "html.parser").select_one("span")

    assert normalize_spaces(snippet.text) == expected_message

    if snippet.has_attr("class"):
        assert snippet["class"] == [expected_class]
    else:
        assert expected_class is None


@pytest.mark.parametrize(
    "template_type",
    (
        "email",
        "letter",
        "banana",
    ),
)
def test_content_count_json_endpoint_for_unsupported_template_types(
    client_request,
    template_type,
):
    client_request.post(
        "main.count_content_length",
        service_id=SERVICE_ONE_ID,
        template_type=template_type,
        content="foo",
        _expected_status=404,
    )


@pytest.mark.parametrize(
    "invalid_pages, page_requested, overlay_expected",
    (
        ("[1, 2]", 1, True),
        ("[1, 2]", 2, True),
        ("[1, 2]", 3, False),
        ("[]", 1, False),
    ),
)
def test_letter_attachment_preview_image_shows_overlay_when_content_outside_printable_area(
    client_request,
    fake_uuid,
    invalid_pages,
    page_requested,
    overlay_expected,
    mocker,
):
    mocker.patch(
        "app.main.views_nl.templates.get_attachment_pdf_and_metadata",
        return_value=(
            "pdf_file",
            {
                "message": "content-outside-printable-area",
                "invalid_pages": invalid_pages,
            },
        ),
    )
    template_preview_mock_valid = mocker.patch(
        "app.template_preview_client.get_png_for_valid_pdf_page",
        return_value=make_response("page.html", 200),
    )
    template_preview_mock_invalid = mocker.patch(
        "app.template_preview_client.get_png_for_invalid_pdf_page",
        return_value=make_response("page.html", 200),
    )

    client_request.get_response(
        "no_cookie.view_invalid_letter_attachment_as_preview",
        file_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        page=page_requested,
    )

    if overlay_expected:
        template_preview_mock_invalid.assert_called_once_with("pdf_file", page_requested, is_an_attachment=True)
        assert template_preview_mock_valid.called is False
    else:
        template_preview_mock_valid.assert_called_once_with("pdf_file", page_requested)
        assert template_preview_mock_invalid.called is False
