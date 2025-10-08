import json
import uuid
from collections import namedtuple
from functools import partial
from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest
from flask import url_for
from freezegun import freeze_time

from app.main.views_nl.dashboard import (
    cache_search_query,
    get_status_filters,
    make_cache_key,
    post_report_request_and_redirect,
)
from app.main.views_nl.jobs import get_time_left
from app.models.service import Service
from app.utils import SEVEN_DAYS_TTL, get_sha512_hashed
from tests.conftest import (
    SERVICE_ONE_ID,
    create_active_caseworking_user,
    create_active_user_empty_permissions,
    create_active_user_view_permissions,
    create_active_user_with_permissions,
    create_notifications,
    normalize_spaces,
)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "user,extra_args,expected_update_endpoint,expected_limit_days,page_title",
    [
        (
            create_active_user_view_permissions(),
            {"message_type": "email"},
            "/email.json",
            7,
            "Emails",
        ),
        (
            create_active_user_view_permissions(),
            {"message_type": "sms"},
            "/sms.json",
            7,
            "Text messages",
        ),
        (
            create_active_caseworking_user(),
            {},
            ".json",
            None,
            "Sent messages",
        ),
    ],
)
@pytest.mark.parametrize(
    "status_argument, expected_api_call",
    [
        (
            "",
            [
                "created",
                "pending",
                "sending",
                "pending-virus-check",
                "delivered",
                "sent",
                "returned-letter",
                "failed",
                "temporary-failure",
                "permanent-failure",
                "technical-failure",
                "virus-scan-failed",
                "validation-failed",
            ],
        ),
        ("sending", ["sending", "created", "pending", "pending-virus-check"]),
        ("delivered", ["delivered", "sent", "returned-letter"]),
        (
            "failed",
            [
                "failed",
                "temporary-failure",
                "permanent-failure",
                "technical-failure",
                "virus-scan-failed",
                "validation-failed",
            ],
        ),
    ],
)
@pytest.mark.parametrize("page_argument, expected_page_argument", [(1, 1), (22, 22), (None, 1)])
@pytest.mark.parametrize(
    "to_argument, expected_to_argument",
    [
        ("", ""),
        ("+447900900123", "+447900900123"),
        ("test@example.com", "test@example.com"),
    ],
)
@freeze_time("2020-01-01 01:00")
def test_can_show_notifications(
    client_request,
    service_one,
    mock_get_notifications,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_has_no_jobs,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
    user,
    extra_args,
    expected_update_endpoint,
    expected_limit_days,
    page_title,
    status_argument,
    expected_api_call,
    page_argument,
    expected_page_argument,
    to_argument,
    expected_to_argument,
    mock_cache_search_query,
):
    client_request.login(user)
    hash_search_query = get_sha512_hashed(to_argument) if to_argument else ""
    if expected_to_argument:
        page = client_request.post(
            "main.view_notifications",
            service_id=SERVICE_ONE_ID,
            status=status_argument,
            search_query=hash_search_query,
            page=page_argument,
            _data={"to": to_argument},
            _expected_status=200,
            **extra_args,
        )
    else:
        page = client_request.get(
            "main.view_notifications",
            service_id=SERVICE_ONE_ID,
            status=status_argument,
            page=page_argument,
            **extra_args,
        )

    first_row = page.select_one("tbody tr")
    assert normalize_spaces(first_row.select_one("a.file-list-filename.govuk-link").text) == (
        # Comes from
        # https://github.com/alphagov/notifications-admin/blob/8faffad508f9a087b0006989c197741c693cc2e2/tests/__init__.py#L436
        "07123456789"
    )
    assert normalize_spaces(
        # We’re doing str() here not .text to make sure there’s no extra
        # HTML sneaking in
        str(first_row.select_one(".file-list-hint"))
    ) == (
        # Comes from
        # https://github.com/alphagov/notifications-admin/blob/8faffad508f9a087b0006989c197741c693cc2e2/tests/__init__.py#L271
        "template content"
    ) or (
        # Comes from
        # https://github.com/alphagov/notifications-admin/blob/8faffad508f9a087b0006989c197741c693cc2e2/tests/__init__.py#L273
        "template subject"
    )

    assert normalize_spaces(first_row.select_one(".table-field-right-aligned .align-with-message-body").text) == (
        "Delivered 1 January at 1:01am"
    )

    assert page_title in page.select_one("h1").text.strip()

    path_to_json = page.select_one("div[data-key=notifications]")["data-resource"]

    url = urlparse(path_to_json)
    assert url.path == f"/services/{SERVICE_ONE_ID}/notifications{expected_update_endpoint}"
    query_dict = parse_qs(url.query)
    if status_argument:
        assert query_dict["status"] == [status_argument]
    if expected_page_argument:
        assert query_dict["page"] == [str(expected_page_argument)]
    assert "to" not in query_dict

    mock_get_notifications.assert_called_with(
        limit_days=expected_limit_days,
        page=expected_page_argument,
        service_id=SERVICE_ONE_ID,
        status=expected_api_call,
        template_type=list(extra_args.values()),
        to=expected_to_argument,
    )

    json_response = client_request.get_response(
        "json_updates.get_notifications_page_partials_as_json",
        service_id=service_one["id"],
        status=status_argument,
        **extra_args,
    )
    json_content = json.loads(json_response.get_data(as_text=True))
    assert json_content.keys() == {"counts", "notifications", "service_data_retention_days"}

    # All links to view individual notifications should pass through the statuses for the current view,
    # so that backlinks can be generated correctly.
    view_notification_links = page.select(".file-list-filename")
    assert all(
        parse_qs(urlparse(view_notification_link["href"]).query, keep_blank_values=True)["from_statuses"]
        == [status_argument]
        for view_notification_link in view_notification_links
    )

    if hash_search_query:
        assert all(
            parse_qs(urlparse(view_notification_link["href"]).query, keep_blank_values=True)["from_search_query"]
            == [hash_search_query]
            for view_notification_link in view_notification_links
        )


def test_can_show_notifications_if_data_retention_not_available(
    client_request,
    mock_get_notifications,
    mock_get_service_statistics,
    mock_has_no_jobs,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
):
    page = client_request.get(
        "main.view_notifications",
        service_id=SERVICE_ONE_ID,
        status="sending,delivered,failed",
    )
    assert page.select_one("h1").text.strip() == "Messages"


@pytest.mark.parametrize(
    "user, query_parameters, notifications_count,expected_download_link",
    [
        (
            create_active_user_with_permissions(),
            {},
            100,
            partial(
                url_for,
                ".download_notifications_csv",
                message_type=None,
            ),
        ),
        (
            create_active_user_with_permissions(),
            {"status": "failed"},
            100,
            partial(url_for, ".download_notifications_csv", status="failed"),
        ),
        (
            create_active_user_with_permissions(),
            {"message_type": "sms"},
            100,
            partial(
                url_for,
                ".download_notifications_csv",
                message_type="sms",
            ),
        ),
        (
            create_active_user_view_permissions(),
            {},
            100,
            partial(
                url_for,
                ".download_notifications_csv",
            ),
        ),
        (
            create_active_caseworking_user(),
            {},
            100,
            lambda service_id: None,
        ),
        (
            create_active_user_with_permissions(),
            {},
            300000,  # Above the threshold, should return None
            lambda service_id: None,
        ),
    ],
    ids=[
        "Active user - no filters",
        "Active user - failed status",
        "Active user - SMS message type",
        "View permissions user - no filters",
        "Caseworking user - no download link",
        "Active user - notifications count above threshold, no download link",
    ],
)
@mock.patch("app.main.views_nl.dashboard.REPORT_REQUEST_MAX_NOTIFICATIONS", 0)
def test_link_to_download_notifications(
    client_request,
    mock_get_notifications,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_has_no_jobs,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
    user,
    query_parameters,
    notifications_count,
    expected_download_link,
):
    mock_get_notifications_count_for_service.return_value = notifications_count

    client_request.login(user)
    page = client_request.get("main.view_notifications", service_id=SERVICE_ONE_ID, **query_parameters)
    download_link = page.select_one("a[href*='download-notifications.csv']")
    assert (download_link["href"] if download_link else None) == expected_download_link(service_id=SERVICE_ONE_ID)


@pytest.mark.parametrize("message_type", ["email", "sms", "letter"])
@pytest.mark.parametrize(
    "given_status, expected_status",
    [
        ("sending,delivered,failed", "all"),
        (None, "all"),
        ("sending", "sending"),
        ("delivered", "delivered"),
        ("failed", "failed"),
    ],
)
def test_view_notifications_calls_report_request_method_with_expected_args(
    client_request,
    mock_get_notifications_count_for_service,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_notifications,
    fake_uuid,
    message_type,
    given_status,
    expected_status,
    mocker,
):
    mock_create_report_request = mocker.patch("app.report_request_api_client.create_report_request")

    kwargs = {
        "message_type": message_type,
        "service_id": SERVICE_ONE_ID,
        "_data": {"report_type": "notifications_status_csv"},
    }
    if given_status:
        kwargs["status"] = given_status

    client_request.post("main.view_notifications", **kwargs)

    mock_create_report_request.assert_called_once_with(
        SERVICE_ONE_ID,
        "notifications_status_csv",
        {
            "user_id": mocker.ANY,
            "report_type": "notifications_status_csv",
            "notification_type": message_type,
            "notification_status": expected_status,
        },
    )


@pytest.mark.parametrize(
    "user, notifications_count, expect_download_link",
    [
        (
            create_active_user_view_permissions(),
            900000,
            True,
        ),
        (
            create_active_user_empty_permissions(),
            500,
            False,
        ),
        (
            create_active_user_empty_permissions(),
            900002,  # Above the threshold, should return None
            False,
        ),
    ],
)
@mock.patch("app.main.views_nl.dashboard.REPORT_REQUEST_MAX_NOTIFICATIONS", 900001)
def test_report_request_notifications_link(
    client_request,
    mocker,
    fake_uuid,
    mock_get_notifications,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_has_no_jobs,
    mock_get_no_api_keys,
    user,
    mock_get_notifications_count_for_service,
    notifications_count,
    expect_download_link,
):
    client_request.login(user)
    mock_get_notifications_count_for_service.return_value = notifications_count

    page = client_request.get("main.view_notifications", service_id=SERVICE_ONE_ID)
    report_request_link = page.select_one("button.govuk-button--as-link")

    if expect_download_link:
        assert report_request_link is not None

        mocker.patch("app.report_request_api_client.create_report_request", return_value=fake_uuid)
        client_request.post(
            "main.view_notifications",
            service_id=SERVICE_ONE_ID,
            message_type="email",
            _data={"report_type": "notifications_status_csv"},
            _expected_status=302,
            _expected_redirect=url_for(
                "main.report_request",
                service_id=SERVICE_ONE_ID,
                report_request_id=fake_uuid,
            ),
        )
    else:
        assert report_request_link is None


def test_download_not_available_to_users_without_dashboard(
    client_request,
    active_caseworking_user,
):
    client_request.login(active_caseworking_user)
    client_request.get(
        "main.download_notifications_csv",
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


@pytest.mark.parametrize(
    "message_type, expected_status",
    (
        (None, 404),
        ("blah", 404),
    ),
)
def test_download_not_available_to_users_if_invalid_message_type(
    client_request,
    message_type,
    expected_status,
    mock_get_service_data_retention,
    mock_get_notifications,
):
    client_request.get(
        "main.download_notifications_csv",
        service_id=SERVICE_ONE_ID,
        message_type=message_type,
        _expected_status=expected_status,
    )


def test_letters_with_status_virus_scan_failed_shows_a_failure_description(
    client_request,
    service_one,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_notifications_count_for_service,
    mock_get_api_keys,
    mocker,
):
    notifications = create_notifications(
        template_type="letter",
        status="virus-scan-failed",
        is_precompiled_letter=True,
        client_reference="client reference",
    )
    mocker.patch("app.models.notification.Notifications._get_items", return_value=notifications)

    page = client_request.get(
        "main.view_notifications",
        service_id=service_one["id"],
        message_type="letter",
        status="",
    )

    error_description = page.select_one("div.table-field-status-error").text.strip()
    assert "Virus detected\n" in error_description


@pytest.mark.parametrize("letter_status", ["pending-virus-check", "virus-scan-failed"])
def test_should_not_show_preview_link_for_precompiled_letters_in_virus_states(
    client_request,
    service_one,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
    letter_status,
    mocker,
):
    notifications = create_notifications(
        template_type="letter", status=letter_status, is_precompiled_letter=True, client_reference="ref"
    )
    mocker.patch("app.models.notification.Notifications._get_items", return_value=notifications)

    page = client_request.get(
        "main.view_notifications",
        service_id=service_one["id"],
        message_type="letter",
        status="",
    )

    assert not page.select_one("a.file-list-filename")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_shows_message_when_no_notifications(
    client_request,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_notifications_with_no_notifications,
    mock_get_notifications_count_for_service,
    mock_get_no_api_keys,
):
    page = client_request.get(
        "main.view_notifications",
        service_id=SERVICE_ONE_ID,
        message_type="sms",
    )

    assert normalize_spaces(page.select("tbody tr")[0].text) == "No messages found (messages are kept for 7 days)"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "initial_query_arguments,form_post_data,expected_search_box_label,expected_search_box_contents",
    [
        (
            {},
            {},
            "Search by recipient",
            None,
        ),
        (
            {
                "message_type": "sms",
            },
            {},
            "Search by phone number",
            None,
        ),
        (
            {
                "message_type": "sms",
            },
            {
                "to": "+33(0)5-12-34-56-78",
            },
            "Search by phone number",
            "+33(0)5-12-34-56-78",
        ),
        (
            {
                "status": "failed",
                "message_type": "email",
                "page": "99",
            },
            {
                "to": "test@example.com",
            },
            "Search by email address",
            "test@example.com",
        ),
        (
            {
                "message_type": "letter",
            },
            {
                "to": "Firstname Lastname",
            },
            "Search by postal address or file name",
            "Firstname Lastname",
        ),
    ],
)
def test_search_recipient_form(
    client_request,
    mock_get_notifications,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
    initial_query_arguments,
    form_post_data,
    expected_search_box_label,
    expected_search_box_contents,
    mocker,
):
    search_term = form_post_data.get("to", "")
    message_type = initial_query_arguments.get("message_type", None)
    hash_search_query = get_sha512_hashed(search_term) if bool(search_term) else None

    mocker.patch("app.main.views_nl.dashboard.cache_search_query", return_value=(hash_search_query, search_term))

    if search_term:
        page = client_request.post(
            "main.view_notifications",
            service_id=SERVICE_ONE_ID,
            _data=form_post_data,
            search_query=hash_search_query,
            _expected_status=200,
            **initial_query_arguments,
        )

        assert page.select_one("form")["method"] == "post"
        action_url = page.select_one("form")["action"]
        url = urlparse(action_url)
        assert url.path == "/services/{}/notifications/{}".format(
            SERVICE_ONE_ID, initial_query_arguments.get("message_type", "")
        ).rstrip("/")
        query_dict = parse_qs(url.query)

        if hash_search_query:
            assert query_dict["search_query"] == [hash_search_query]
        else:
            assert query_dict == {}

        assert page.select_one("label[for=to]").text.strip() == expected_search_box_label

        recipient_inputs = page.select("input[name=to]")
        assert len(recipient_inputs) == 2

        for field in recipient_inputs:
            assert field.get("value") == expected_search_box_contents
    else:
        client_request.post(
            "main.view_notifications",
            service_id=SERVICE_ONE_ID,
            search_query=hash_search_query,
            _data=form_post_data,
            _expected_status=302,
            _expected_redirect=url_for(
                "main.view_notifications",
                service_id=SERVICE_ONE_ID,
                message_type=message_type,
            ),
            **initial_query_arguments,
        )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "message_type, expected_search_box_label",
    [
        (None, "Search by recipient or reference"),
        ("sms", "Search by phone number or reference"),
        ("email", "Search by email address or reference"),
        ("letter", "Search by postal address, file name or reference"),
    ],
)
def test_api_users_are_told_they_can_search_by_reference_when_service_has_api_keys(
    client_request,
    mock_get_notifications,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_notifications_count_for_service,
    message_type,
    expected_search_box_label,
    mock_get_api_keys,
):
    page = client_request.get(
        "main.view_notifications",
        service_id=SERVICE_ONE_ID,
        message_type=message_type,
    )
    assert page.select_one("label[for=to]").text.strip() == expected_search_box_label


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "message_type, expected_search_box_label",
    [
        (None, "Search by recipient"),
        ("sms", "Search by phone number"),
        ("email", "Search by email address"),
        ("letter", "Search by postal address or file name"),
    ],
)
def test_api_users_are_not_told_they_can_search_by_reference_when_service_has_no_api_keys(
    client_request,
    mock_get_notifications,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_notifications_count_for_service,
    message_type,
    expected_search_box_label,
    mock_get_no_api_keys,
):
    page = client_request.get(
        "main.view_notifications",
        service_id=SERVICE_ONE_ID,
        message_type=message_type,
    )
    assert page.select_one("label[for=to]").text.strip() == expected_search_box_label


def test_should_show_notifications_for_a_service_with_next_previous(
    client_request,
    service_one,
    mock_get_notifications_with_previous_next,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_notifications_count_for_service,
    mock_get_no_api_keys,
):
    page = client_request.get("main.view_notifications", service_id=service_one["id"], message_type="sms", page=2)

    next_page_link = page.select_one("a[rel=next]")
    prev_page_link = page.select_one("a[rel=previous]")
    assert (
        url_for("main.view_notifications", service_id=service_one["id"], message_type="sms", page=3)
        in next_page_link["href"]
    )
    assert "Next page" in next_page_link.text.strip()
    assert "page 3" in next_page_link.text.strip()
    assert (
        url_for("main.view_notifications", service_id=service_one["id"], message_type="sms", page=1)
        in prev_page_link["href"]
    )
    assert "Previous page" in prev_page_link.text.strip()
    assert "page 1" in prev_page_link.text.strip()


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_doesnt_show_pagination_with_search_term(
    client_request,
    service_one,
    mock_get_notifications_with_previous_next,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
):
    to_argument = "test@example.com"
    hash_search_query = get_sha512_hashed(to_argument)
    page = client_request.post(
        "main.view_notifications",
        service_id=service_one["id"],
        message_type="sms",
        search_query=hash_search_query,
        _data={
            "to": to_argument,
        },
        _expected_status=200,
    )
    assert len(page.select("tbody tr")) == 50
    assert not page.select_one("a[rel=next]")
    assert not page.select_one("a[rel=previous]")
    assert normalize_spaces(page.select_one(".table-show-more-link").text) == "Only showing the first 50 messages"


@pytest.mark.parametrize(
    "job_created_at, expected_message",
    [
        ("2016-01-10 11:09:00.000000+00:00", "Data available for 7 days"),
        ("2016-01-04 11:09:00.000000+00:00", "Data available for 1 day"),
        ("2016-01-03 11:09:00.000000+00:00", "Data available for 12 hours"),
        ("2016-01-02 23:59:59.000000+00:00", "Data no longer available"),
    ],
)
@freeze_time("2016-01-10 12:00:00.000000")
def test_time_left(job_created_at, expected_message):
    assert get_time_left(job_created_at) == expected_message


STATISTICS = {"sms": {"requested": 6, "failed": 2, "delivered": 1}}


def test_get_status_filters_calculates_stats(client_request):
    ret = get_status_filters(Service({"id": "foo"}), "sms", STATISTICS, None)

    assert {label: count for label, _option, _link, count in ret} == {
        "total": 6,
        "delivering": 3,
        "failed": 2,
        "delivered": 1,
    }


def test_get_status_filters_in_right_order(client_request):
    ret = get_status_filters(Service({"id": "foo"}), "sms", STATISTICS, None)

    assert [label for label, _option, _link, _count in ret] == ["total", "delivering", "delivered", "failed"]


def test_get_status_filters_constructs_links(client_request):
    ret = get_status_filters(Service({"id": "foo"}), "sms", STATISTICS, None)

    link = ret[0][2]
    assert link == "/services/foo/notifications/sms?status=sending,delivered,failed"


def test_get_status_filters_constructs_search_query(client_request):
    ret = get_status_filters(Service({"id": "foo"}), "sms", STATISTICS, "test_hash")

    link = ret[0][2]
    assert link == "/services/foo/notifications/sms?status=sending,delivered,failed&search_query=test_hash"


def test_html_contains_notification_id(
    client_request,
    service_one,
    mock_get_notifications,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
):
    page = client_request.get(
        "main.view_notifications",
        service_id=service_one["id"],
        message_type="sms",
        status="",
    )

    notifications = page.select("tbody tr")
    for tr in notifications:
        assert uuid.UUID(tr.attrs["id"])


def test_html_contains_links_for_failed_notifications(
    client_request,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
    mocker,
):
    notifications = create_notifications(status="technical-failure")
    mocker.patch("app.models.notification.Notifications._get_items", return_value=notifications)

    response = client_request.get(
        "main.view_notifications", service_id=SERVICE_ONE_ID, message_type="sms", status="sending%2Cdelivered%2Cfailed"
    )
    notifications = response.select("tbody tr")
    for tr in notifications:
        link_text = tr.select_one("div.table-field-status-error a").text
        assert normalize_spaces(link_text) == "Technical failure"


@pytest.mark.parametrize(
    "notification_type, expected_row_contents",
    (
        ("sms", "07123456789 hello & welcome hidden"),
        ("email", "example@gov.uk hidden, hello & welcome"),
        (
            "letter",
            (
                # Letters don’t support redaction, but this test is still
                # worthwhile to show that the ampersand is not double-escaped
                "1 Example Street ((name)), hello & welcome"
            ),
        ),
    ),
)
def test_redacts_templates_that_should_be_redacted(
    client_request,
    mocker,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_no_api_keys,
    notification_type,
    mock_get_notifications_count_for_service,
    expected_row_contents,
):
    notifications = create_notifications(
        status="technical-failure",
        content="hello & welcome ((name))",
        subject="((name)), hello & welcome",
        personalisation={"name": "Jo"},
        redact_personalisation=True,
        template_type=notification_type,
    )
    mocker.patch("app.models.notification.Notifications._get_items", return_value=notifications)

    page = client_request.get(
        "main.view_notifications",
        service_id=SERVICE_ONE_ID,
        message_type=notification_type,
    )

    assert normalize_spaces(page.select("tbody tr th")[0].text) == (expected_row_contents)


@pytest.mark.parametrize("message_type, nav_visible", [("email", True), ("sms", True), ("letter", False)])
def test_big_numbers_dont_show_for_letters(
    client_request,
    service_one,
    mock_get_notifications,
    active_user_with_permissions,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
    message_type,
    nav_visible,
):
    page = client_request.get(
        "main.view_notifications",
        service_id=service_one["id"],
        message_type=message_type,
        status="",
        page=1,
    )

    assert (len(page.select(".pill")) > 0) == nav_visible
    assert (len(page.select("[type=search]")) > 0) is True


@freeze_time("2017-09-27 16:30:00.000000")
@pytest.mark.parametrize(
    "message_type, status, expected_hint_status, single_line",
    [
        ("email", "created", "Delivering since 27 September at 5:30pm", True),
        ("email", "sending", "Delivering since 27 September at 5:30pm", True),
        ("email", "temporary-failure", "Inbox not accepting messages right now 27 September at 5:31pm", False),
        ("email", "permanent-failure", "Email address does not exist 27 September at 5:31pm", False),
        ("email", "delivered", "Delivered 27 September at 5:31pm", True),
        ("sms", "created", "Delivering since 27 September at 5:30pm", True),
        ("sms", "sending", "Delivering since 27 September at 5:30pm", True),
        ("sms", "temporary-failure", "Phone not accepting messages right now 27 September at 5:31pm", False),
        ("sms", "permanent-failure", "Not delivered 27 September at 5:31pm", False),
        ("sms", "delivered", "Delivered 27 September at 5:31pm", True),
        ("letter", "created", "27 September at 5:30pm", True),
        ("letter", "pending-virus-check", "27 September at 5:30pm", True),
        ("letter", "sending", "27 September at 5:30pm", True),
        ("letter", "delivered", "27 September at 5:30pm", True),
        ("letter", "received", "27 September at 5:30pm", True),
        ("letter", "accepted", "27 September at 5:30pm", True),
        (
            "letter",
            "cancelled",
            "27 September at 5:30pm",
            False,
        ),  # The API won’t return cancelled letters
        (
            "letter",
            "permanent-failure",
            "Permanent failure 27 September at 5:31pm",
            False,
        ),
        (
            "letter",
            "temporary-failure",
            "27 September at 5:30pm",
            False,
        ),  # Not currently a real letter status
        ("letter", "virus-scan-failed", "Virus detected 27 September at 5:30pm", False),
        (
            "letter",
            "validation-failed",
            "Validation failed 27 September at 5:30pm",
            False,
        ),
        (
            "letter",
            "technical-failure",
            "Technical failure 27 September at 5:30pm",
            False,
        ),
    ],
)
def test_sending_status_hint_displays_correctly_on_notifications_page(
    client_request,
    service_one,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
    message_type,
    status,
    expected_hint_status,
    single_line,
    mocker,
):
    notifications = create_notifications(template_type=message_type, status=status)
    mocker.patch("app.models.notification.Notifications._get_items", return_value=notifications)

    page = client_request.get("main.view_notifications", service_id=service_one["id"], message_type=message_type)

    assert normalize_spaces(page.select(".table-field-right-aligned")[0].text) == expected_hint_status
    assert bool(page.select(".align-with-message-body")) is single_line


@pytest.mark.parametrize(
    "is_precompiled_letter,expected_address,expected_hint",
    [
        (True, "Full Name\nFirst address line\npostcode", "ref"),
        (False, "Full Name\nFirst address line\npostcode", "template subject"),
    ],
)
def test_should_show_address_and_hint_for_letters(
    client_request,
    service_one,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
    mocker,
    is_precompiled_letter,
    expected_address,
    expected_hint,
):
    notifications = create_notifications(
        template_type="letter",
        subject=expected_hint,
        is_precompiled_letter=is_precompiled_letter,
        client_reference=expected_hint,
        to=expected_address,
    )
    mocker.patch("app.models.notification.Notifications._get_items", return_value=notifications)

    page = client_request.get(
        "main.view_notifications",
        service_id=SERVICE_ONE_ID,
        message_type="letter",
    )

    assert page.select_one("a.file-list-filename").text == "Full Name, First address line, postcode"
    assert page.select_one("p.file-list-hint").text.strip() == expected_hint


CanDownloadLinkTestCase = namedtuple(
    "SupportLinkTestCase",
    ["notifications_count", "can_download", "expected_download_link_present", "expected_support_link_present"],
)


@pytest.mark.parametrize(
    "test_case",
    [
        CanDownloadLinkTestCase(
            notifications_count=100,
            can_download=True,
            expected_download_link_present=True,
            expected_support_link_present=False,
        ),
        CanDownloadLinkTestCase(
            notifications_count=250001,
            can_download=False,
            expected_download_link_present=False,
            expected_support_link_present=True,
        ),
    ],
    ids=[
        "Below threshold - Download link present, support link not present",
        "Above threshold - Download link not present, support link present",
    ],
)
@mock.patch("app.main.views_nl.dashboard.REPORT_REQUEST_MAX_NOTIFICATIONS", 0)
def test_view_notifications_can_download(
    client_request,
    mock_get_notifications,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_has_no_jobs,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
    test_case: CanDownloadLinkTestCase,
):
    mock_get_notifications_count_for_service.return_value = test_case.notifications_count

    page = client_request.get("main.view_notifications", service_id=SERVICE_ONE_ID)

    # check download link
    download_link = page.select_one("a[href*='download-notifications.csv']")
    if test_case.expected_download_link_present:
        assert download_link is not None
    else:
        assert download_link is None

    # check support link
    support_link = page.select_one("a[href*='/support/ask-question-give-feedback']")
    if test_case.expected_support_link_present:
        assert support_link is not None
    else:
        assert support_link is None


@pytest.mark.parametrize(
    "test_case",
    [
        CanDownloadLinkTestCase(
            notifications_count=100,
            can_download=True,
            expected_download_link_present=True,
            expected_support_link_present=False,
        ),
        CanDownloadLinkTestCase(
            notifications_count=900000,
            can_download=True,
            expected_download_link_present=False,
            expected_support_link_present=True,
        ),
    ],
    ids=[
        "Below threshold - Report request download link present, support link not present",
        "Above threshold - Report request download link not present, support link present",
    ],
)
@mock.patch("app.main.views_nl.dashboard.REPORT_REQUEST_MAX_NOTIFICATIONS", 850000)
def test_download_link_and_report_request_notifications(
    client_request,
    mock_get_notifications,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_has_no_jobs,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
    test_case: CanDownloadLinkTestCase,
):
    mock_get_notifications_count_for_service.return_value = test_case.notifications_count

    page = client_request.get("main.view_notifications", service_id=SERVICE_ONE_ID)

    # check report request download link
    report_request_link = page.select_one("button.govuk-button--as-link")
    if test_case.expected_download_link_present:
        assert report_request_link is not None
    else:
        assert report_request_link is None

    # when report request feature is ON, the old download link should not be present
    old_download_link = page.select_one("a[href*='download-notifications.csv']")
    assert old_download_link is None

    # check support link
    support_link = page.select_one("a[href*='/support/ask-question-give-feedback']")
    if test_case.expected_support_link_present:
        assert support_link is not None
    else:
        assert support_link is None


def test_make_cache_key():
    key = make_cache_key("test1hash123456", "service-test-id-1234")
    assert key == "service-service-test-id-1234-notification-search-query-hash-test1hash123456"


def test_create_cache_when_search_query_does_not_exist(mocker):
    search_term = "test@example.com"
    search_query_hash = ""
    expected_hash = get_sha512_hashed(search_term)

    mock_redis_set = mocker.patch(
        "app.extensions.RedisClient.set",
    )
    mock_redis_get = mocker.patch(
        "app.extensions.RedisClient.get",
        return_value=None,
    )

    cached_search_query_hash, cached_search_term = cache_search_query(search_term, SERVICE_ONE_ID, search_query_hash)

    assert not mock_redis_get.called
    mock_redis_set.assert_called_once_with(
        make_cache_key(expected_hash, SERVICE_ONE_ID),
        search_term,
        ex=SEVEN_DAYS_TTL,
    )
    assert cached_search_query_hash == expected_hash
    assert cached_search_term == search_term


def test_return_when_search_query_exists(mocker):
    search_term = ""
    search_query_hash = get_sha512_hashed("1234567")
    excepted_search_term = "1234567"

    mock_redis_set = mocker.patch(
        "app.extensions.RedisClient.set",
    )
    mock_redis_get = mocker.patch(
        "app.extensions.RedisClient.get",
        return_value=b"1234567",
    )

    cached_search_query_hash, cached_search_term = cache_search_query(search_term, SERVICE_ONE_ID, search_query_hash)

    mock_redis_get.assert_called_once_with(make_cache_key(search_query_hash, SERVICE_ONE_ID))
    assert not mock_redis_set.called
    assert cached_search_query_hash == search_query_hash
    assert cached_search_term == excepted_search_term


def test_return_when_different_search_term_and_search_query(mocker):
    search_term = "test@example.com"
    search_query_hash = get_sha512_hashed("1234567")
    expected_hash = get_sha512_hashed(search_term)

    mock_redis_set = mocker.patch(
        "app.extensions.RedisClient.set",
    )
    mock_redis_get = mocker.patch(
        "app.extensions.RedisClient.get",
        return_value=b"1234567",
    )

    cached_search_query_hash, cached_search_term = cache_search_query(search_term, SERVICE_ONE_ID, search_query_hash)

    mock_redis_get.assert_called_once_with(make_cache_key(search_query_hash, SERVICE_ONE_ID))
    mock_redis_set.assert_called_once_with(
        make_cache_key(expected_hash, SERVICE_ONE_ID),
        search_term,
        ex=SEVEN_DAYS_TTL,
    )
    assert cached_search_query_hash == expected_hash
    assert cached_search_term == search_term


def test_return_when_same_search_term_and_search_query(mocker):
    search_term = "1234567"
    search_query_hash = get_sha512_hashed("1234567")
    expected_hash = get_sha512_hashed(search_term)

    mock_redis_set = mocker.patch(
        "app.extensions.RedisClient.set",
    )
    mock_redis_get = mocker.patch(
        "app.extensions.RedisClient.get",
        return_value=b"1234567",
    )

    cached_search_query_hash, cached_search_term = cache_search_query(search_term, SERVICE_ONE_ID, search_query_hash)

    mock_redis_get.assert_called_once_with(make_cache_key(search_query_hash, SERVICE_ONE_ID))
    assert not mock_redis_set.called
    assert cached_search_query_hash == expected_hash
    assert cached_search_term == search_term


@pytest.fixture(scope="function")
def mock_cache_search_query(mocker, to_argument):
    def _get_cache(search_term, service_id, search_query_hash):
        if search_query_hash:
            return search_query_hash, to_argument
        elif search_term:
            hash_search_query = get_sha512_hashed(search_term) if bool(search_term) else None
            return hash_search_query, search_term
        return "", ""

    return mocker.patch("app.main.views_nl.dashboard.cache_search_query", side_effect=_get_cache)


@pytest.mark.parametrize(
    "status_argument, page_argument, to_argument, expected_to_argument",
    [
        ("sending", 1, "", ""),
        ("pending", 3, "+447900900123", "+447900900123"),
        ("delivered", 4, "test@example.com", "test@example.com"),
    ],
)
def test_with_existing_search_query(
    client_request,
    service_one,
    mock_get_notifications,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
    status_argument,
    page_argument,
    to_argument,
    expected_to_argument,
    mocker,
    mock_cache_search_query,
):
    client_request.login(create_active_user_view_permissions())
    hash_search_query = get_sha512_hashed(to_argument) if to_argument else None

    mocker.patch("app.main.views_nl.dashboard.cache_search_query", return_value=(hash_search_query, to_argument))

    page = client_request.get(
        "main.view_notifications",
        service_id=SERVICE_ONE_ID,
        status=status_argument,
        search_query=hash_search_query,
        page=page_argument,
    )
    if expected_to_argument:
        assert page.select_one("input[id=to]")["value"] == expected_to_argument
    else:
        assert "value" not in page.select_one("input[id=to]")


@pytest.mark.parametrize(
    "status_argument, page_argument, to_argument, expected_to_argument",
    [
        ("sending", 1, "", ""),
        ("pending", 3, "+447900900123", "+447900900123"),
        ("delivered", 4, "test@example.com", "test@example.com"),
    ],
)
def test_search_should_generate_search_query(
    client_request,
    service_one,
    mock_get_notifications,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
    status_argument,
    page_argument,
    to_argument,
    expected_to_argument,
    mocker,
    mock_cache_search_query,
):
    client_request.login(create_active_user_view_permissions())
    hash_search_query = get_sha512_hashed(expected_to_argument) if expected_to_argument else ""

    client_request.post(
        "main.view_notifications",
        service_id=SERVICE_ONE_ID,
        status=status_argument,
        _data={"to": to_argument},
        page=page_argument,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.view_notifications",
            service_id=SERVICE_ONE_ID,
            search_query=hash_search_query,
        ),
    )

    mock_cache_search_query.assert_called_with(to_argument, SERVICE_ONE_ID, "")


def test_ajax_blocks_have_same_resource(
    client_request,
    service_one,
    mock_get_notifications,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_no_api_keys,
    mock_get_notifications_count_for_service,
):
    page = client_request.get(
        "main.view_notifications",
        service_id=service_one["id"],
        message_type="sms",
        status="",
    )

    ajax_blocks = page.select("[data-notify-module=update-content]")

    assert len(ajax_blocks) == 2
    for block in ajax_blocks:
        assert block["data-resource"] == url_for(
            "json_updates.get_notifications_page_partials_as_json",
            service_id=service_one["id"],
            message_type="sms",
            # we manually define the statuses even though they're implicit in the initial html GET
            status="sending,delivered,failed",
            page=1,
            search_query=None,
        )
        # ensure both ajax blocks have a data-form, so that they both issue the same POST request to the json endpoint
        assert block["data-form"] == "search-form"
    assert {block["data-key"] for block in ajax_blocks} == {"counts", "notifications"}


def test_view_notifications_post_report_request(
    client_request,
    mock_get_service,
    mocker,
):
    mocker.patch(
        "app.notify_client.report_request_api_client.ReportRequestClient.post",
        return_value={"data": {"id": "mock_report_request_id"}},
    )

    mock_current_user = create_active_user_with_permissions()

    mock_create_report_request = mocker.patch(
        "app.main.views_nl.dashboard.report_request_api_client.create_report_request",
        return_value="mock_report_request_id",
    )
    report_type = "notifications_report"
    message_type = "email"
    status = "delivered"
    response = post_report_request_and_redirect(mock_get_service, report_type, message_type, status)

    mock_create_report_request.assert_called_once_with(
        mock_get_service.id,
        report_type,
        {
            "user_id": mock_current_user["id"],
            "report_type": report_type,
            "notification_type": message_type,
            "notification_status": status,
        },
    )

    assert response.status_code == 302
    assert response.location == url_for(
        "main.report_request",
        service_id=mock_get_service.id,
        report_request_id="mock_report_request_id",
    )
