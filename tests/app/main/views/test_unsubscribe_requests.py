from unittest.mock import Mock, call

import pytest
from flask import url_for
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError

from app import service_api_client
from app.models.unsubscribe_requests_report import UnsubscribeRequestsReports
from tests.conftest import SERVICE_ONE_ID, create_unsubscribe_request_report, normalize_spaces


@pytest.mark.parametrize(
    "test_data, expected_rows, expected_grey_text_statuses",
    (
        (
            # A mixture of reports from different dates
            [
                create_unsubscribe_request_report(
                    earliest_timestamp="2024-06-22T15:00:00+00:00",
                    latest_timestamp="2024-06-22T15:00:00+00:00",
                ),
                create_unsubscribe_request_report(
                    earliest_timestamp="2024-06-22T11:00:00+00:00",
                    latest_timestamp="2024-06-22T13:17:00+00:00",
                    batch_id="af5f5e86-528b-475e-8be1-012988987775",
                ),
                create_unsubscribe_request_report(
                    count=34,
                    earliest_timestamp="2024-06-22T10:00:00+00:00",
                    latest_timestamp="2024-06-22T11:00:00+00:00",
                    batch_id="5e2b05ef-7552-49ef-a77f-96d46ab2b9bb",
                ),
                create_unsubscribe_request_report(
                    count=200,
                    earliest_timestamp="2024-06-15T18:00:00+00:00",
                    latest_timestamp="2024-06-21T08:00:00+00:00",
                    batch_id="c2d11916-ee82-419e-99a8-7e38163e756f",
                ),
                create_unsubscribe_request_report(
                    count=321,
                    earliest_timestamp="2023-12-8T00:00:00+00:00",
                    latest_timestamp="2024-01-14T00:00:00+00:00",
                    processed_by_service_at="2024-06-10T00:00:00+00:00",
                    batch_id="e5aed7fe-b649-43b0-9c2b-1cdeb315f724",
                ),
            ],
            [
                "Report Status",
                "Today at 4:00pm 1 unsubscribe request Not downloaded",
                "Today from midday to 2:17pm 1 unsubscribe request Downloaded",
                "Today until midday 34 unsubscribe requests Downloaded",
                "15 June to yesterday 200 unsubscribe requests Downloaded",
                "7 December 2023 to 13 January 321 unsubscribe requests Completed",
            ],
            [
                "Not downloaded",
            ],
        ),
        (
            # A single report spanning a long time period
            [
                create_unsubscribe_request_report(
                    service_id=SERVICE_ONE_ID,
                    earliest_timestamp="2020-01-01T10:00:00+00:00",
                    latest_timestamp="2024-06-01T12:17:00+00:00",
                    batch_id="af5f5e86-528b-475e-8be1-012988987775",
                ),
            ],
            [
                "Report Status",
                "1 January 2020 to 1 June 1 unsubscribe request Downloaded",
            ],
            [],
        ),
        (
            # Two single requests on the same day
            [
                create_unsubscribe_request_report(
                    earliest_timestamp="2024-01-01T13:18:00+00:00",
                    latest_timestamp="2024-01-01T13:18:00+00:00",
                    batch_id="af5f5e86-528b-475e-8be1-012988987775",
                ),
                create_unsubscribe_request_report(
                    earliest_timestamp="2024-01-01T12:17:00+00:00",
                    latest_timestamp="2024-01-01T12:17:00+00:00",
                    batch_id="c2d11916-ee82-419e-99a8-7e38163e756f",
                ),
            ],
            [
                "Report Status",
                "1 January at 1:18pm 1 unsubscribe request Downloaded",
                "1 January at 12:17pm 1 unsubscribe request Downloaded",
            ],
            [],
        ),
        (
            # Two reports with overlapping days
            [
                create_unsubscribe_request_report(
                    earliest_timestamp="2024-05-01T11:00:00+00:00",
                    latest_timestamp="2024-05-01T13:17:00+00:00",
                    processed_by_service_at="2024-06-22T13:14:00+00:00",
                    batch_id="af5f5e86-528b-475e-8be1-012988987775",
                ),
                create_unsubscribe_request_report(
                    count=12345678,
                    earliest_timestamp="2024-04-30T03:00:00+00:00",
                    latest_timestamp="2024-05-01T09:00:00+00:00",
                    processed_by_service_at="2024-06-22T13:14:00+00:00",
                    batch_id="c2d11916-ee82-419e-99a8-7e38163e756f",
                ),
            ],
            [
                "Report Status",
                "1 May from midday to 2:17pm 1 unsubscribe request Completed",
                "30 April to 1 May at 10:00am 12,345,678 unsubscribe requests Completed",
            ],
            [],
        ),
        (
            # Three reports on independent, consecutive days
            [
                create_unsubscribe_request_report(
                    count=1234,
                    earliest_timestamp="2024-06-22T11:00:00+00:00",
                    latest_timestamp="2024-06-22T13:17:00+00:00",
                    batch_id="af5f5e86-528b-475e-8be1-012988987775",
                ),
                create_unsubscribe_request_report(
                    count=4567,
                    earliest_timestamp="2024-06-21T11:00:00+00:00",
                    latest_timestamp="2024-06-21T13:17:00+00:00",
                    batch_id="c2d11916-ee82-419e-99a8-7e38163e756f",
                ),
                create_unsubscribe_request_report(
                    count=7890,
                    earliest_timestamp="2024-06-20T11:00:00+00:00",
                    latest_timestamp="2024-06-20T13:17:00+00:00",
                    batch_id="e5aed7fe-b649-43b0-9c2b-1cdeb315f724",
                ),
            ],
            [
                "Report Status",
                "Today 1,234 unsubscribe requests Downloaded",
                "Yesterday 4,567 unsubscribe requests Downloaded",
                "20 June 7,890 unsubscribe requests Downloaded",
            ],
            [],
        ),
        (
            # Three reports on the same day
            [
                create_unsubscribe_request_report(
                    count=1234,
                    earliest_timestamp="2024-06-01T22:22:00+00:00",
                    latest_timestamp="2024-06-01T23:00:00+00:00",
                    batch_id="af5f5e86-528b-475e-8be1-012988987775",
                ),
                create_unsubscribe_request_report(
                    count=4567,
                    earliest_timestamp="2024-06-01T13:17:00+00:00",
                    latest_timestamp="2024-06-01T13:18:00+00:00",
                    batch_id="c2d11916-ee82-419e-99a8-7e38163e756f",
                ),
                create_unsubscribe_request_report(
                    count=7890,
                    earliest_timestamp="2024-06-01T08:00:00+00:00",
                    latest_timestamp="2024-06-01T11:00:00+00:00",
                    batch_id="e5aed7fe-b649-43b0-9c2b-1cdeb315f724",
                ),
            ],
            [
                "Report Status",
                "1 June from 11:22pm to midnight 1,234 unsubscribe requests Downloaded",
                "1 June from 2:17pm to 2:18pm 4,567 unsubscribe requests Downloaded",
                "1 June until midday 7,890 unsubscribe requests Downloaded",
            ],
            [],
        ),
    ),
)
@freeze_time("2024-06-22 22:22:22")
def test_unsubscribe_request_reports_summary(
    client_request,
    mocker,
    test_data,
    expected_rows,
    expected_grey_text_statuses,
):
    mocker.patch.object(UnsubscribeRequestsReports, "_get_items", return_value=test_data)

    page = client_request.get("main.unsubscribe_request_reports_summary", service_id=SERVICE_ONE_ID)

    assert [normalize_spaces(row.text) for row in page.select("tr")] == expected_rows
    assert [
        normalize_spaces(field.text)
        for field in page.select("td.table-field-right-aligned .table-field-status-default .align-with-message-body")
    ] == expected_grey_text_statuses


def test_no_unsubscribe_request_reports_summary_to_display(client_request, mocker):
    mocker.patch.object(UnsubscribeRequestsReports, "_get_items", return_value=[])

    page = client_request.get("main.unsubscribe_request_reports_summary", service_id=SERVICE_ONE_ID)

    assert ["Report Status", "If you have any email unsubscribe requests they will be listed here"] == [
        normalize_spaces(row.text) for row in page.select("tr")
    ]


@freeze_time("2024-06-22 12:00")
@pytest.mark.parametrize(
    "will_be_archived_at, expected_deletion_message",
    (
        ("2024-06-29 23:59", "This report will be deleted in 7 days from now."),
        ("2024-06-23 12:00", "This report will be deleted in a day from now."),
        ("2024-06-22 13:59", "This report will be deleted today."),
    ),
)
def test_unsubscribe_request_report_for_unprocessed_batched_reports(
    client_request,
    mocker,
    will_be_archived_at,
    expected_deletion_message,
):
    test_data = [
        create_unsubscribe_request_report(
            count=200,
            earliest_timestamp="2024-06-15",
            latest_timestamp="2024-06-21",
            batch_id="a8a526f9-84be-44a6-b751-62c95c4b9329",
            will_be_archived_at=will_be_archived_at,
        ),
    ]

    mocker.patch.object(UnsubscribeRequestsReports, "_get_items", return_value=test_data)

    page = client_request.get(
        "main.unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=test_data[0]["batch_id"],
    )
    assert page.select("h1")[0].text == "15 June to yesterday"
    checkbox = page.select("#report_has_been_processed")[0].attrs
    checkbox_hint = page.select("#report_has_been_processed-item-hint")[0].text
    unsubscribe_requests_count_text = page.select("#report-unsubscribe-requests-count")[0].text
    availability_date = page.select("#unsubscribe_report_availability")[0].text
    update_button = page.select("#process_unsubscribe_report")
    download_link = page.select_one("main ol li a")
    assert download_link["href"] == url_for(
        "main.download_unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=test_data[0]["batch_id"],
    )
    assert normalize_spaces(download_link.text) == "Download the report"
    assert "disabled" not in checkbox
    assert normalize_spaces(checkbox_hint) == "I have unsubscribed these recipients from our mailing list"
    assert normalize_spaces(unsubscribe_requests_count_text) == "200 new unsubscribe requests"
    assert len(update_button) == 1
    assert normalize_spaces(availability_date) == expected_deletion_message


@freeze_time("2024-07-02")
def test_unsubscribe_request_report_for_unbatched_reports(client_request, mocker):
    test_data = [
        create_unsubscribe_request_report(
            count=34,
            earliest_timestamp="2024-06-22 10:00",
            latest_timestamp="2024-07-01 12:00",
        ),
    ]

    mocker.patch.object(UnsubscribeRequestsReports, "_get_items", return_value=test_data)
    page = client_request.get(
        "main.unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=test_data[0]["batch_id"],
    )
    checkbox = page.select("#report_has_been_processed")[0].attrs
    checkbox_hint = page.select("#report_has_been_processed-item-hint")[0].text
    unsubscribe_requests_count_text = page.select("#report-unsubscribe-requests-count")[0].text
    availability_date = page.select("#unsubscribe_report_availability")[0].text
    update_button = page.select("#process_unsubscribe_report")
    assert page.select("h1")[0].text == "22 June to yesterday"
    download_link = page.select_one("main ol li a")
    assert download_link["href"] == url_for(
        "main.download_unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=test_data[0]["batch_id"],
    )
    assert normalize_spaces(download_link.text) == "Download the report"
    assert "disabled" in checkbox
    assert normalize_spaces(checkbox_hint) == "You cannot do this until you’ve downloaded the report"
    assert normalize_spaces(unsubscribe_requests_count_text) == "34 new unsubscribe requests"
    assert normalize_spaces(availability_date) == (
        "Once downloaded, reports are available for 7 days. "
        "Requests which have not been downloaded will be deleted after 90 days."
    )
    assert len(update_button) == 0


@freeze_time("2024-01-01")
def test_unsubscribe_request_report_for_processed_batched_reports(client_request, mocker):
    test_data = [
        create_unsubscribe_request_report(
            count=321,
            earliest_timestamp="2023-06-8",
            latest_timestamp="2023-06-14",
            processed_by_service_at="2024-06-10",
            batch_id="e5aed7fe-b649-43b0-9c2b-1cdeb315f724",
            will_be_archived_at="2024-01-08 23:00",
        ),
    ]
    mocker.patch.object(UnsubscribeRequestsReports, "_get_items", return_value=test_data)
    page = client_request.get(
        "main.unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=test_data[0]["batch_id"],
    )
    assert page.select("h1")[0].text == "8 June 2023 to 14 June 2023"
    checkbox = page.select("#report_has_been_processed")[0].attrs
    checkbox_hint = page.select("#report_has_been_processed-item-hint")[0].text
    availability_date = page.select("#unsubscribe_report_availability")[0].text
    "completed_unsubscribe_report_main_text"
    update_button = page.select("#process_unsubscribe_report")
    assert page.select_one("p a[download]")["href"] == url_for(
        "main.download_unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=test_data[0]["batch_id"],
    )
    assert "disabled" not in checkbox
    assert "checked" in checkbox
    assert normalize_spaces(checkbox_hint) == "I have unsubscribed these recipients from our mailing list"
    assert normalize_spaces(availability_date) == "This report will be deleted in 7 days from now."
    assert len(update_button) == 1


def test_unsubscribe_request_report_with_forced_download(
    client_request,
    mocker,
    fake_uuid,
):
    mocker.patch.object(
        UnsubscribeRequestsReports,
        "_get_items",
        return_value=[
            create_unsubscribe_request_report(
                count=321,
                earliest_timestamp="2023-06-8",
                latest_timestamp="2023-06-14",
                batch_id=fake_uuid,
                will_be_archived_at="2024-01-08 23:00",
            ),
        ],
    )
    page = client_request.get(
        "main.unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=fake_uuid,
        force_download="true",
    )
    download_url = url_for(
        "main.download_unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=fake_uuid,
    )
    assert page.select_one("head meta[http-equiv=refresh]")["content"] == f"0;URL='{download_url}'"


def test_cannot_force_download_for_unbatched_unsubscribe_request_report(
    client_request,
    mocker,
):
    mocker.patch.object(
        UnsubscribeRequestsReports,
        "_get_items",
        return_value=[
            create_unsubscribe_request_report(
                count=321,
                earliest_timestamp="2023-06-8",
                latest_timestamp="2023-06-14",
            ),
        ],
    )
    page = client_request.get(
        "main.unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=None,
        force_download="true",
    )
    assert not page.select("head meta[http-equiv=refresh]")


@pytest.mark.parametrize("batch_id", ["32b4e359-d4df-49b6-a92b-2eaa9343cfdd", None])
def test_non_existing_unsubscribe_request_report_batch_id_returns_404(client_request, mocker, batch_id):
    mocker.patch.object(UnsubscribeRequestsReports, "_get_items", return_value=[])
    page = client_request.get(
        "main.unsubscribe_request_report",
        _expected_status=404,
        service_id=SERVICE_ONE_ID,
        batch_id=batch_id,
    )
    assert normalize_spaces(page.select("h1")[0].text) == "Page not found"


@freeze_time("2024-08-07")
def test_mark_report_as_completed(client_request, mocker, fake_uuid):
    mocker.patch.object(
        UnsubscribeRequestsReports,
        "_get_items",
        return_value=[
            create_unsubscribe_request_report(
                count=321,
                earliest_timestamp="2024-08-06",
                latest_timestamp="2024-08-07",
                batch_id=fake_uuid,
            ),
        ],
    )
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete")
    mock_post = mocker.patch.object(service_api_client, "post")
    page = client_request.post(
        "main.unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=fake_uuid,
        _data={
            "report_has_been_processed": True,
        },
        _follow_redirects=True,
    )
    mock_post.assert_called_once_with(
        f"service/{SERVICE_ONE_ID}/process-unsubscribe-request-report/{fake_uuid}",
        data={"report_has_been_processed": True},
    )
    assert mock_redis_delete.call_args_list == [
        call(f"service-{SERVICE_ONE_ID}-unsubscribe-request-reports-summary", raise_exception=True),
        call(f"service-{SERVICE_ONE_ID}-unsubscribe-request-statistics", raise_exception=True),
        call(f"service-{SERVICE_ONE_ID}-unsubscribe-request-statistics", raise_exception=True),
        call(f"service-{SERVICE_ONE_ID}-unsubscribe-request-reports-summary", raise_exception=True),
    ]
    assert normalize_spaces(page.select_one("main .banner-default-with-tick")) == (
        "Report for yesterday to today marked as completed"
    )


def test_download_unsubscribe_request_report_redirects_to_batch_unsubscribe_request_report_endpoint_no_batch_id(
    client_request,
):
    client_request.get(
        "main.download_unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=None,
        _expected_redirect=url_for(
            "main.create_unsubscribe_request_report",
            service_id=SERVICE_ONE_ID,
        ),
    )


def test_create_unsubscribe_request_report_creates_batched_report(client_request, mocker):
    summary_data = [
        create_unsubscribe_request_report(
            count=34,
            earliest_timestamp="2024-07-18T16:32:28.000000Z",
            latest_timestamp="2024-07-20T19:22:11.000000Z",
        ),
    ]
    test_batch_id = "daaa3f82-faf0-4199-82da-15ec6aa8abe8"
    mocker.patch.object(UnsubscribeRequestsReports, "_get_items", return_value=summary_data)
    mock_batch_report = mocker.patch.object(
        service_api_client, "create_unsubscribe_request_report", return_value={"report_id": test_batch_id}
    )
    client_request.get(
        "main.create_unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        _expected_redirect=url_for(
            "main.unsubscribe_request_report",
            service_id=SERVICE_ONE_ID,
            batch_id=test_batch_id,
            force_download="true",
        ),
    )
    mock_batch_report.assert_called_once_with(
        SERVICE_ONE_ID,
        {
            "count": 34,
            "earliest_timestamp": "2024-07-18T16:32:28.000000Z",
            "latest_timestamp": "2024-07-20T19:22:11.000000Z",
        },
    )


def test_create_unsubscribe_request_report_blocks_platform_admin(
    client_request,
    platform_admin_user,
    fake_uuid,
):
    client_request.login(platform_admin_user)
    client_request.get(
        "main.create_unsubscribe_request_report",
        service_id=fake_uuid,
        _expected_status=403,
    )


def test_download_unsubscribe_request_report(client_request, mocker):
    report_data = {
        "batch_id": "3d466625-6ea4-414f-ac48-add30d895c43",
        "earliest_timestamp": "Thu, 18 Jul 2024 15:32:28 GMT",
        "latest_timestamp": "Sat, 20 Jul 2024 18:22:11 GMT",
        "unsubscribe_requests": [
            {
                "email_address": "fizz@bar.com",
                "template_name": "Template Fizz",
                "original_file_name": "Contact List 2",
                "template_sent_at": "Tue, 16 Jul 2024 17:44:20 GMT",
                "unsubscribe_request_received_at": "Thu, 18 Jul 2024 17:44:20 GMT",
            },
            {
                "email_address": "fizzbuzz@bar.com",
                "template_name": "Template FizzBuzz",
                "original_file_name": "N/A",
                "template_sent_at": "Wed, 17 Jul 2024 17:44:20 GMT",
                "unsubscribe_request_received_at": "Fri, 19 Jul 2024 17:44:20 GMT",
            },
        ],
    }

    mock_get_report = mocker.patch.object(
        service_api_client, "get_unsubscribe_request_report", return_value=report_data
    )

    response = client_request.get_response(
        "main.download_unsubscribe_request_report", service_id=SERVICE_ONE_ID, batch_id=report_data["batch_id"]
    )

    mock_get_report.assert_called_once_with(SERVICE_ONE_ID, report_data["batch_id"])
    report = response.get_data(as_text=True)

    assert (
        report.strip() == "Email address,Template name,Uploaded spreadsheet file name,"
        "Template sent at,Unsubscribe request received at\r\n"
        'fizz@bar.com,Template Fizz,Contact List 2,"Tue, 16 Jul 2024 17:44:20 GMT","Thu, 18 Jul 2024 17:44:20 GMT"\r\n'
        'fizzbuzz@bar.com,Template FizzBuzz,N/A,"Wed, 17 Jul 2024 17:44:20 GMT","Fri, 19 Jul 2024 17:44:20 GMT"'
    )


def test_unsubscribe_example_page(client_request):
    page = client_request.get(
        "main.unsubscribe_example",
        _test_for_elements_without_class=False,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Are you sure you want to unsubscribe?"
    assert normalize_spaces(page.select_one("p").text) == (
        "If you want to unsubscribe you will no longer receive these emails."
    )
    assert page.select_one("form[method=post]")["action"] == "/unsubscribe/example"
    assert normalize_spaces(page.select_one("form[method=post] button[type=submit]").text) == "Confirm"
    assert normalize_spaces(page.select_one("footer p").text) == (
        "This is an example page only with no further action needed."
    )


def test_unsubscribe_example_confirmation_page(client_request, fake_uuid):
    page = client_request.get(
        "main.unsubscribe_example_confirmed",
        _test_for_elements_without_class=False,
    )
    assert normalize_spaces(page.select_one("h1").text) == "We have your request to unsubscribe"
    assert normalize_spaces(page.select_one("p").text) == (
        "It can take a few days to unsubscribe you from these emails."
    )
    assert normalize_spaces(page.select_one("footer p").text) == (
        "This is an example page only with no further action needed."
    )
    assert not page.select_one("form")


def test_unsubscribe_landing_page(client_request, fake_uuid):
    page = client_request.get(
        "main.unsubscribe",
        notification_id=fake_uuid,
        token="abc123",
        _test_for_elements_without_class=False,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Are you sure you want to unsubscribe?"
    assert page.select_one("form[method=post]")["action"] == f"/unsubscribe/{fake_uuid}/abc123"
    assert normalize_spaces(page.select_one("form[method=post] button[type=submit]").text) == "Confirm"


def test_unsubscribe_valid_request(
    client_request,
    fake_uuid,
    mocker,
):
    mock_unsubscribe = mocker.patch("app.unsubscribe_api_client.unsubscribe", return_value=True)
    client_request.post(
        "main.unsubscribe",
        notification_id=fake_uuid,
        token="abc123",
        _expected_redirect=url_for("main.unsubscribe_confirmed"),
        _test_for_elements_without_class=False,
    )
    mock_unsubscribe.assert_called_once_with(fake_uuid, "abc123")


def test_unsubscribe_confirmation_page(client_request):
    page = client_request.get(
        "main.unsubscribe_confirmed",
        _test_for_elements_without_class=False,
    )
    assert normalize_spaces(page.select_one("h1").text) == "We have your request to unsubscribe"
    assert normalize_spaces(page.select_one("p").text) == "It can take a few days to unsubscribe you from these emails."
    assert not page.select_one("form")


def test_unsubscribe_request_not_found(
    client_request,
    fake_uuid,
    mocker,
):
    def _post(notification_id, token):
        raise HTTPError(response=Mock(status_code=404))

    mock_post = mocker.patch("app.unsubscribe_api_client.post", side_effect=_post)

    page = client_request.post(
        "main.unsubscribe",
        notification_id=fake_uuid,
        token="abc123",
        _expected_status=404,
        _test_for_elements_without_class=False,
    )

    mock_post.assert_called_once_with(f"/unsubscribe/{fake_uuid}/abc123", None)

    assert normalize_spaces(page.select_one("h1").text) == "There is a problem"
    assert [normalize_spaces(p.text) for p in page.select("p")] == [
        "We could not unsubscribe you from these emails.",
        "If you pasted the web address from an email, check you copied the entire address.",
    ]
