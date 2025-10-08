import json
import uuid
from datetime import UTC, datetime

import pytest
from flask import url_for
from freezegun import freeze_time

from app.main.views_nl.jobs import get_time_left
from tests import NotifyBeautifulSoup, job_json, notification_json, user_json
from tests.conftest import (
    SERVICE_ONE_ID,
    create_active_caseworking_user,
    create_active_user_with_permissions,
    create_notifications,
    create_template,
    normalize_spaces,
)


def test_old_jobs_hub_redirects(
    client_request,
):
    client_request.get(
        "main.view_jobs",
        service_id=SERVICE_ONE_ID,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.uploads",
            service_id=SERVICE_ONE_ID,
        ),
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "user",
    [
        create_active_user_with_permissions(),
        create_active_caseworking_user(),
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
@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_page_for_one_job(
    client_request,
    mock_get_service_template,
    mock_get_job,
    mock_get_notifications,
    mock_get_service_data_retention,
    fake_uuid,
    status_argument,
    expected_api_call,
    user,
):
    client_request.login(user)
    page = client_request.get("main.view_job", service_id=SERVICE_ONE_ID, job_id=fake_uuid, status=status_argument)

    assert page.select_one("h1").text.strip() == "thisisatest.csv"
    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.uploads",
        service_id=SERVICE_ONE_ID,
    )
    assert " ".join(page.select_one("tbody").find("tr").text.split()) == (
        "07123456789 template content Delivered 1 January at 11:10am"
    )
    assert page.select_one("div[data-key=notifications]")["data-resource"] == url_for(
        "json_updates.view_job_updates",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        status=status_argument,
    )
    csv_link = page.select_one("a[id=download-job-report]")
    assert csv_link["href"] == url_for(
        "main.view_job_csv", service_id=SERVICE_ONE_ID, job_id=fake_uuid, status=status_argument
    )
    assert csv_link.text == "Download this report (CSV)"
    assert page.select_one("span#time-left").text == "Data available for 7 days"
    assert page.select_one("#job-notifications")
    assert normalize_spaces(page.select_one("tbody tr").text) == normalize_spaces(
        "07123456789 template content Delivered 1 January at 11:10am"
    )
    assert page.select_one("tbody tr a")["href"] == url_for(
        "main.view_notification",
        service_id=SERVICE_ONE_ID,
        notification_id="00000000-0000-0000-0000-000000000000",
        from_job=fake_uuid,
    )

    mock_get_notifications.assert_called_with(SERVICE_ONE_ID, fake_uuid, status=expected_api_call)


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_page_for_one_job_with_flexible_data_retention(
    client_request,
    mock_get_service_template,
    mock_get_job,
    mock_get_notifications,
    mock_get_service_data_retention,
    fake_uuid,
):
    mock_get_service_data_retention.side_effect = [[{"days_of_retention": 10, "notification_type": "sms"}]]
    page = client_request.get("main.view_job", service_id=SERVICE_ONE_ID, job_id=fake_uuid, status="delivered")

    assert page.select_one("span#time-left").text == "Data available for 10 days"
    assert "Cancel sending these letters" not in page


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_get_jobs_should_tell_user_if_more_than_one_page(
    client_request,
    fake_uuid,
    service_one,
    mock_get_job,
    mock_get_service_template,
    mock_get_notifications_with_previous_next,
    mock_get_service_data_retention,
):
    page = client_request.get(
        "main.view_job",
        service_id=service_one["id"],
        job_id=fake_uuid,
        status="",
    )
    assert page.select_one("p.table-show-more-link").text.strip() == "Only showing the first 50 rows"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_job_in_progress(
    client_request,
    service_one,
    mock_get_service_template,
    mock_get_job_in_progress,
    mock_get_notifications,
    mock_get_service_data_retention,
    fake_uuid,
):
    page = client_request.get(
        "main.view_job",
        service_id=service_one["id"],
        job_id=fake_uuid,
    )
    assert [normalize_spaces(link.text) for link in page.select(".pill a:not(.pill-item--selected)")] == [
        "10 delivering text messages",
        "0 delivered text messages",
        "0 failed text messages",
    ]
    assert page.select_one("p.hint").text.strip() == "Report is 50% complete…"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_job_without_notifications(
    client_request,
    service_one,
    mock_get_service_template,
    mock_get_job_in_progress,
    mock_get_notifications_with_no_notifications,
    mock_get_service_data_retention,
    fake_uuid,
):
    page = client_request.get(
        "main.view_job",
        service_id=service_one["id"],
        job_id=fake_uuid,
    )
    assert [normalize_spaces(link.text) for link in page.select(".pill a:not(.pill-item--selected)")] == [
        "10 delivering text messages",
        "0 delivered text messages",
        "0 failed text messages",
    ]
    assert page.select_one("p.hint").text.strip() == "Report is 50% complete…"
    assert page.select_one("tbody").text.strip() == "No messages to show yet…"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_job_with_sending_limit_exceeded_status(
    client_request,
    service_one,
    mock_get_service_template,
    mock_get_job_with_sending_limits_exceeded,
    mock_get_notifications_with_no_notifications,
    mock_get_service_data_retention,
    fake_uuid,
):
    page = client_request.get(
        "main.view_job",
        service_id=service_one["id"],
        job_id=fake_uuid,
    )

    assert normalize_spaces(page.select("main p")[1].text) == (
        "Notify cannot send these messages because you have reached your daily limit. You can only send 1,000 text messages per day."  # noqa
    )
    assert normalize_spaces(page.select("main p")[2].text) == (
        "Upload this spreadsheet again tomorrow or contact the GOV.UK Notify team to raise the limit."
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2020-01-10 1:0:0")
@pytest.mark.parametrize(
    "created_at, processing_started, expected_message",
    (
        # Recently created, not yet started
        (datetime(2020, 1, 10, 0, 0, 0), None, "No messages to show yet…"),
        # Just started
        (datetime(2020, 1, 10, 0, 0, 0), datetime(2020, 1, 10, 0, 0, 1), "No messages to show yet…"),
        # Created a while ago, just started
        (datetime(2020, 1, 1, 0, 0, 0), datetime(2020, 1, 10, 0, 0, 1), "No messages to show yet…"),
        # Created a while ago, started just within the last 24h
        (datetime(2020, 1, 1, 0, 0, 0), datetime(2020, 1, 9, 1, 0, 1), "No messages to show yet…"),
        # Created a while ago, started exactly 24h ago
        (
            datetime(2020, 1, 1, 0, 0, 0),
            datetime(2020, 1, 9, 1, 0, 0),
            "No messages to show",
        ),
        # Processed but the data retention period has elapsed
        (
            datetime(2020, 1, 1, 0, 0, 0),
            datetime(2020, 1, 2, 1, 0, 0),
            "These messages have been deleted because they were sent more than 7 days ago",
        ),
    ),
)
def test_should_show_old_job(
    client_request,
    service_one,
    active_user_with_permissions,
    mock_get_service_template,
    mocker,
    mock_get_notifications_with_no_notifications,
    mock_get_service_data_retention,
    fake_uuid,
    created_at,
    processing_started,
    expected_message,
):
    mocker.patch(
        "app.job_api_client.get_job",
        return_value={
            "data": job_json(
                SERVICE_ONE_ID,
                active_user_with_permissions,
                created_at=created_at.replace(tzinfo=UTC).isoformat(),
                processing_started=(processing_started.replace(tzinfo=UTC).isoformat() if processing_started else None),
            ),
        },
    )
    page = client_request.get(
        "main.view_job",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
    )
    assert not page.select(".pill")
    assert not page.select("p.hint")
    assert not page.select("a[download]")
    assert page.select_one("tbody").text.strip() == expected_message
    assert [normalize_spaces(column.text) for column in page.select("main .govuk-grid-column-one-quarter")] == [
        "1 total text messages",
        "1 delivering text message",
        "0 delivered text messages",
        "0 failed text messages",
    ]


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_letter_job(
    client_request,
    mock_get_service_letter_template,
    mock_get_letter_job,
    mock_get_service_data_retention,
    fake_uuid,
    mocker,
):
    notifications = create_notifications(template_type="letter", subject="template subject")
    get_notifications = mocker.patch(
        "app.models.notification.Notifications._get_items",
        return_value=notifications,
    )

    page = client_request.get(
        "main.view_job",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
    )
    assert normalize_spaces(page.select_one("h1").text) == "thisisatest.csv"
    assert normalize_spaces(page.select("p.bottom-gutter")[0].text) == ("Sent by Test User on 1 January at 11:09am")
    assert normalize_spaces(page.select("p#printing-info")[0].text) == ("Printing starts today at 5:30pm")
    assert page.select(".banner-default-with-tick") == []
    assert normalize_spaces(page.select("tbody tr")[0].text) == (
        "1 Example Street template subject 1 January at 11:09am"
    )
    assert normalize_spaces(page.select(".keyline-block")[0].text) == "1 Letter"
    assert normalize_spaces(page.select(".keyline-block")[1].text) == "11 January Estimated delivery date"
    assert page.select_one("a[id=download-job-report]")["href"] == url_for(
        "main.view_job_csv",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
    )
    assert page.select(".hint") == []

    get_notifications.assert_called_with(
        SERVICE_ONE_ID,
        fake_uuid,
        status=[
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
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2016-01-01 11:09:00")
def test_should_show_letter_job_with_banner_after_sending_before_1730(
    client_request,
    mock_get_service_letter_template,
    mock_get_letter_job,
    mock_get_service_data_retention,
    fake_uuid,
    mocker,
):
    mocker.patch(
        "app.models.notification.Notifications._get_items",
        return_value=create_notifications(template_type="letter", postage="second"),
    )

    page = client_request.get(
        "main.view_job",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        just_sent="yes",
    )

    assert page.select("p.bottom-gutter") == []
    assert normalize_spaces(page.select(".banner-default-with-tick")[0].text) == (
        "Your letter has been sent. Printing starts today at 5:30pm."
    )
    assert not page.select_one(".govuk-back-link")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2016-01-01 11:09:00")
def test_should_show_letter_job_with_banner_when_there_are_multiple_CSV_rows(
    client_request,
    mock_get_service_letter_template,
    mock_get_letter_job_in_progress,
    mock_get_service_data_retention,
    fake_uuid,
    mocker,
):
    mocker.patch(
        "app.models.notification.Notifications._get_items",
        return_value=create_notifications(template_type="letter", postage="second"),
    )

    page = client_request.get(
        "main.view_job",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        just_sent="yes",
    )

    assert page.select("p.bottom-gutter") == []
    assert normalize_spaces(page.select(".banner-default-with-tick")[0].text) == (
        "Your letters have been sent. Printing starts today at 5:30pm."
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2016-01-01 18:09:00")
def test_should_show_letter_job_with_banner_after_sending_after_1730(
    client_request,
    mock_get_service_letter_template,
    mock_get_letter_job,
    mock_get_service_data_retention,
    fake_uuid,
    mocker,
):
    mocker.patch(
        "app.models.notification.Notifications._get_items",
        return_value=create_notifications(template_type="letter", postage="second"),
    )

    page = client_request.get(
        "main.view_job",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        just_sent="yes",
    )

    assert page.select("p.bottom-gutter") == []
    assert normalize_spaces(page.select(".banner-default-with-tick")[0].text) == (
        "Your letter has been sent. Printing starts tomorrow at 5:30pm."
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2016-01-01T00:00:00.061258")
def test_should_show_scheduled_job(
    client_request,
    mock_get_service_template,
    mock_get_scheduled_job,
    mock_get_service_data_retention,
    mock_get_notifications,
    fake_uuid,
    mocker,
):
    mocker.patch(
        "app.main.views_nl.jobs.s3download",
        return_value="""
            phone number,name
            +447700900986,John
            +447700900986,Smith
        """,
    )
    page = client_request.get(
        "main.view_job",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        just_sent="yes",
    )

    assert normalize_spaces(page.select("main p")[1].text) == "Sending Two week reminder today at midnight"
    assert page.select("main p a")[0]["href"] == url_for(
        "main.view_template_version",
        service_id=SERVICE_ONE_ID,
        template_id="5d729fbd-239c-44ab-b498-75a985f3198f",
        version=1,
    )
    assert page.select_one("form button").text.strip() == "Cancel sending"
    assert not page.select_one(".govuk-back-link")

    recipients_table = page.select_one(
        "[data-notify-module=remove-in-presence-of][data-target-element-id=job-notifications] "
        '.fullscreen-content[data-notify-module="fullscreen-table"] table'
    )
    assert [normalize_spaces(column_heading.text) for column_heading in recipients_table.select("thead tr th")] == [
        "Row in file1",
        "phone number",
        "name",
    ]
    assert [
        [normalize_spaces(column.text) for column in row.select("th, td")]
        for row in recipients_table.select("tbody tr")
    ] == [
        ["2", "+447700900986", "John"],
        ["3", "+447700900986", "Smith"],
    ]

    download_link = page.select_one(".table-show-more-link a")
    assert normalize_spaces(download_link.text) == "Download this file (CSV)"
    assert download_link["href"] == url_for(
        "main.view_job_original_file_csv",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
    )


def test_should_download_scheduled_job(
    client_request,
    mock_get_scheduled_job,
    fake_uuid,
    mocker,
):
    original_file_contents = "phone number,name\n+447700900986,John\n+447700900986,Smith\n"
    mocker.patch(
        "app.main.views_nl.jobs.s3download",
        return_value=original_file_contents,
    )
    response = client_request.get_response(
        "main.view_job_original_file_csv",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
    )
    assert response.data.decode("utf-8") == original_file_contents
    assert response.headers["Content-Disposition"] == 'inline; filename="thisisatest.csv"'


def test_should_not_download_unscheduled_job(
    client_request,
    mock_get_job,
    mock_get_service_data_retention,
    mock_get_notifications,
    fake_uuid,
    mocker,
):
    client_request.get(
        "main.view_job_original_file_csv",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        _expected_status=404,
    )


def test_should_cancel_job(
    client_request,
    fake_uuid,
    mock_get_job,
    mock_get_service_template,
    mocker,
):
    mock_cancel = mocker.patch("app.job_api_client.cancel_job")
    client_request.post(
        "main.cancel_job",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_dashboard",
            service_id=SERVICE_ONE_ID,
        ),
    )

    mock_cancel.assert_called_once_with(SERVICE_ONE_ID, fake_uuid)


def test_should_not_show_cancelled_job(
    client_request,
    mock_get_cancelled_job,
    fake_uuid,
):
    client_request.get(
        "main.view_job",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        _expected_status=404,
    )


@pytest.mark.parametrize("job_status", ["finished", "finished all notifications created"])
def test_should_cancel_letter_job(
    client_request, job_status, mock_get_service_letter_template, active_user_with_permissions, mocker
):
    job_id = str(uuid.uuid4())
    job = job_json(
        SERVICE_ONE_ID,
        active_user_with_permissions,
        job_id=job_id,
        created_at="2019-06-20T15:30:00.000001+00:00",
        job_status=job_status,
        template_type="letter",
    )
    mocker.patch("app.job_api_client.get_job", side_effect=[{"data": job}])
    notifications_json = notification_json(SERVICE_ONE_ID, job=job, status="created", template_type="letter")
    mocker.patch("app.job_api_client.get_job", side_effect=[{"data": job}])
    mocker.patch("app.models.notification.Notifications._get_items", return_value=notifications_json)
    mocker.patch("app.notification_api_client.get_notification_count_for_job_id", return_value=5)
    mock_cancel = mocker.patch("app.job_api_client.cancel_letter_job", return_value=5)
    client_request.post(
        "main.cancel_letter_job",
        service_id=SERVICE_ONE_ID,
        job_id=job_id,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_dashboard",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_cancel.assert_called_once_with(SERVICE_ONE_ID, job_id)


@freeze_time("2019-06-20 17:30:00.000001")
@pytest.mark.parametrize(
    "job_created_at, expected_fragment",
    [
        ("2019-06-20T15:30:00.000001+00:00", "today"),
        ("2019-06-19T15:30:00.000001+00:00", "yesterday"),
        ("2019-06-18T15:30:00.000001+00:00", "on 18 June"),
    ],
)
def test_should_not_show_cancel_link_for_letter_job_if_too_late(
    client_request,
    mocker,
    mock_get_service_letter_template,
    mock_get_service_data_retention,
    active_user_with_permissions,
    job_created_at,
    expected_fragment,
):
    job_id = uuid.uuid4()
    job = job_json(SERVICE_ONE_ID, active_user_with_permissions, job_id=job_id, created_at=job_created_at)
    notifications_json = notification_json(SERVICE_ONE_ID, job=job, status="created", template_type="letter")
    mocker.patch("app.job_api_client.get_job", side_effect=[{"data": job}])
    mocker.patch("app.models.notification.Notifications._get_items", return_value=notifications_json)

    page = client_request.get("main.view_job", service_id=SERVICE_ONE_ID, job_id=str(job_id))

    assert "Cancel sending these letters" not in page
    assert page.select_one("p#printing-info").text.strip() == f"Printed {expected_fragment} at 5:30pm"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2019-06-20 15:32:00.000001")
@pytest.mark.parametrize("job_status", ["finished", "finished all notifications created", "in progress"])
def test_should_show_cancel_link_for_letter_job(
    client_request,
    mock_get_service_letter_template,
    mock_get_service_data_retention,
    active_user_with_permissions,
    job_status,
    mocker,
):
    job_id = uuid.uuid4()
    job = job_json(
        SERVICE_ONE_ID,
        active_user_with_permissions,
        job_id=job_id,
        created_at="2019-06-20T15:30:00.000001+00:00",
        job_status=job_status,
    )
    notifications_json = notification_json(SERVICE_ONE_ID, job=job, status="created", template_type="letter")
    mocker.patch("app.job_api_client.get_job", side_effect=[{"data": job}])
    mocker.patch(
        "app.models.notification.Notifications._get_items",
        return_value=notifications_json,
    )

    page = client_request.get("main.view_job", service_id=SERVICE_ONE_ID, job_id=str(job_id))

    cancel_link = page.select_one(".page-footer-delete-link-without-button a.govuk-link.govuk-link--destructive")
    assert normalize_spaces(cancel_link.text) == "Cancel sending these letters"
    assert cancel_link["href"] == url_for("main.cancel_letter_job", service_id=SERVICE_ONE_ID, job_id=job_id)
    assert page.select_one("p#printing-info").text.strip() == "Printing starts today at 5:30pm"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2019-06-20 15:31:00.000001")
@pytest.mark.parametrize("job_status,number_of_processed_notifications", [["in progress", 2], ["finished", 1]])
def test_dont_cancel_letter_job_when_too_early_to_cancel(
    client_request,
    mock_get_service_letter_template,
    mock_get_service_data_retention,
    active_user_with_permissions,
    job_status,
    number_of_processed_notifications,
    mocker,
):
    job_id = uuid.uuid4()
    job = job_json(
        SERVICE_ONE_ID,
        active_user_with_permissions,
        job_id=job_id,
        created_at="2019-06-20T15:30:00.000001+00:00",
        job_status=job_status,
        notification_count=2,
    )
    mocker.patch("app.job_api_client.get_job", side_effect=[{"data": job}, {"data": job}])

    notifications_json = notification_json(
        SERVICE_ONE_ID, job=job, status="created", template_type="letter", rows=number_of_processed_notifications
    )
    mocker.patch("app.models.notification.Notifications._get_items", return_value=notifications_json)
    mocker.patch(
        "app.notification_api_client.get_notification_count_for_job_id", return_value=number_of_processed_notifications
    )

    mock_cancel = mocker.patch("app.job_api_client.cancel_letter_job")
    page = client_request.post(
        "main.cancel_letter_job",
        service_id=SERVICE_ONE_ID,
        job_id=str(job_id),
        _expected_status=200,
    )
    assert mock_cancel.called is False
    flash_message = normalize_spaces(page.select_one("div.banner-dangerous").text)

    assert "We are still processing these letters, please try again in a minute." in flash_message


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2016-01-01 00:00:00.000001")
def test_should_show_updates_for_one_job_as_json(
    client_request,
    service_one,
    mock_get_notifications,
    mock_get_service_template,
    mock_get_job,
    mock_get_service_data_retention,
    fake_uuid,
):
    response = client_request.get_response(
        "json_updates.view_job_updates",
        service_id=service_one["id"],
        job_id=fake_uuid,
    )

    content = json.loads(response.get_data(as_text=True))
    assert "sending" in content["counts"]
    assert "delivered" in content["counts"]
    assert "failed" in content["counts"]
    assert "Recipient" in content["notifications"]
    assert "07123456789" in content["notifications"]
    assert "Status" in content["notifications"]
    assert "Delivered" in content["notifications"]
    assert "12:01am" in content["notifications"]
    assert "Sent by Test User on 1 January at midnight" in content["status"]


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2016-01-01 00:00:00.000001")
def test_should_show_updates_for_scheduled_job_as_json(
    client_request,
    service_one,
    mock_get_notifications,
    mock_get_service_template,
    mock_get_service_data_retention,
    mocker,
    fake_uuid,
):
    mocker.patch(
        "app.job_api_client.get_job",
        return_value={
            "data": job_json(
                service_one["id"],
                created_by=user_json(),
                job_id=fake_uuid,
                scheduled_for="2016-06-01T13:00:00+00:00",
                processing_started="2016-06-01T15:00:00+00:00",
            )
        },
    )

    response = client_request.get_response(
        "json_updates.view_job_updates",
        service_id=service_one["id"],
        job_id=fake_uuid,
    )

    content = response.json
    assert "sending" in content["counts"]
    assert "delivered" in content["counts"]
    assert "failed" in content["counts"]
    assert "Recipient" in content["notifications"]
    assert "07123456789" in content["notifications"]
    assert "Status" in content["notifications"]
    assert "Delivered" in content["notifications"]
    assert "12:01am" in content["notifications"]
    assert "Sent by Test User on 1 June at 4:00pm" in content["status"]


@freeze_time("2016-01-01 00:00:00")
def test_should_show_updates_for_upcoming_scheduled_job_as_json(
    client_request,
    service_one,
    mock_get_notifications,
    mock_get_service_template,
    mock_get_service_data_retention,
    mocker,
    fake_uuid,
):
    mocker.patch(
        "app.job_api_client.get_job",
        return_value={
            "data": job_json(
                SERVICE_ONE_ID,
                created_by=user_json(),
                job_id=fake_uuid,
                scheduled_for="2016-06-01T13:00:00+00:00",
                job_status="scheduled",
                processing_started=None,
            )
        },
    )

    response_json = client_request.get_response(
        "json_updates.view_job_updates",
        service_id=service_one["id"],
        job_id=fake_uuid,
    ).json

    form = NotifyBeautifulSoup(response_json["notifications"], "html.parser").select_one("form")

    assert form["method"] == "post"
    assert form["action"] == url_for(
        "main.cancel_job",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
    )
    assert form.select_one("button")


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


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_letter_job_with_first_class_if_notifications_are_first_class(
    client_request,
    mock_get_service_letter_template,
    mock_get_letter_job,
    mock_get_service_data_retention,
    fake_uuid,
    mocker,
):
    notifications = create_notifications(template_type="letter", postage="first")
    mocker.patch("app.models.notification.Notifications._get_items", return_value=notifications)

    page = client_request.get(
        "main.view_job",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
    )

    assert normalize_spaces(page.select(".keyline-block")[1].text) == "5 January Estimated delivery date"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_letter_job_with_first_class_if_no_notifications(
    client_request,
    service_one,
    mock_get_letter_job,
    fake_uuid,
    mock_get_notifications_with_no_notifications,
    mock_get_service_data_retention,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={"data": create_template(template_type="letter", postage="first")},
    )

    page = client_request.get(
        "main.view_job",
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
    )

    assert normalize_spaces(page.select(".keyline-block")[1].text) == "5 January Estimated delivery date"
