import pytest
from freezegun import freeze_time

from app import service_api_client
from app.models.unsubscribe_requests_report import UnsubscribeRequestsReports
from tests.conftest import SERVICE_ONE_ID, normalize_spaces


@pytest.mark.parametrize(
    "test_data, expected_rows",
    (
        (
            # A mixture of reports from different dates
            [
                {
                    "count": 1,
                    "earliest_timestamp": "2024-06-22 14:00",
                    "latest_timestamp": "2024-06-22 14:00",
                    "processed_by_service_at": None,
                    "batch_id": "1629dada-9777-4d0a-aa5a-a8b6e3c7ff7b",
                    "is_a_batched_report": False,
                },
                {
                    "count": 1,
                    "earliest_timestamp": "2024-06-22 10:00",
                    "latest_timestamp": "2024-06-22 12:17",
                    "processed_by_service_at": None,
                    "batch_id": "af5f5e86-528b-475e-8be1-012988987775",
                    "is_a_batched_report": False,
                },
                {
                    "count": 34,
                    "earliest_timestamp": "2024-06-22 09:00",
                    "latest_timestamp": "2024-06-22 10:00",
                    "processed_by_service_at": None,
                    "batch_id": "5e2b05ef-7552-49ef-a77f-96d46ab2b9bb",
                    "is_a_batched_report": True,
                },
                {
                    "count": 200,
                    "earliest_timestamp": "2024-06-15 18:00",
                    "latest_timestamp": "2024-06-21 08:00",
                    "processed_by_service_at": None,
                    "batch_id": "c2d11916-ee82-419e-99a8-7e38163e756f",
                    "is_a_batched_report": True,
                },
                {
                    "count": 321,
                    "earliest_timestamp": "2023-12-8",
                    "latest_timestamp": "2024-01-14",
                    "processed_by_service_at": "2024-06-10",
                    "batch_id": "e5aed7fe-b649-43b0-9c2b-1cdeb315f724",
                    "is_a_batched_report": True,
                },
            ],
            [
                "Report Status",
                "Today at 4:00pm 1 unsubscribe request Not downloaded",
                "Today at midday to today at 2:17pm 1 unsubscribe request Not downloaded",
                "Today until midday 34 unsubscribe requests Downloaded",
                "15 June to yesterday 200 unsubscribe requests Downloaded",
                "7 December 2023 to 13 January 321 unsubscribe requests Completed",
            ],
        ),
        (
            # A single report spanning a long time period
            [
                {
                    "count": 1,
                    "earliest_timestamp": "2020-01-01 10:00",
                    "latest_timestamp": "2024-06-01 12:17",
                    "processed_by_service_at": None,
                    "batch_id": "af5f5e86-528b-475e-8be1-012988987775",
                    "is_a_batched_report": False,
                },
            ],
            [
                "Report Status",
                "1 January 2020 to 1 June 1 unsubscribe request Not downloaded",
            ],
        ),
        (
            # Two reports with overlapping days
            [
                {
                    "count": 1,
                    "earliest_timestamp": "2024-05-01 10:00",
                    "latest_timestamp": "2024-05-01 12:17",
                    "processed_by_service_at": "2024-06-22 13:14",
                    "batch_id": "af5f5e86-528b-475e-8be1-012988987775",
                    "is_a_batched_report": True,
                },
                {
                    "count": 12345678,
                    "earliest_timestamp": "2024-04-30 02:00",
                    "latest_timestamp": "2024-05-01 08:00",
                    "processed_by_service_at": "2024-06-22 13:14",
                    "batch_id": "c2d11916-ee82-419e-99a8-7e38163e756f",
                    "is_a_batched_report": True,
                },
            ],
            [
                "Report Status",
                "1 May at midday to 1 May at 2:17pm 1 unsubscribe request Completed",
                "30 April to 1 May at 10:00am 12,345,678 unsubscribe requests Completed",
            ],
        ),
        (
            # Three reports on independent, consecutive days
            [
                {
                    "count": 1234,
                    "earliest_timestamp": "2024-06-22 10:00",
                    "latest_timestamp": "2024-06-22 12:17",
                    "processed_by_service_at": None,
                    "batch_id": "af5f5e86-528b-475e-8be1-012988987775",
                    "is_a_batched_report": True,
                },
                {
                    "count": 4567,
                    "earliest_timestamp": "2024-06-21 10:00",
                    "latest_timestamp": "2024-06-21 12:17",
                    "processed_by_service_at": None,
                    "batch_id": "c2d11916-ee82-419e-99a8-7e38163e756f",
                    "is_a_batched_report": True,
                },
                {
                    "count": 7890,
                    "earliest_timestamp": "2024-06-20 10:00",
                    "latest_timestamp": "2024-06-20 12:17",
                    "processed_by_service_at": None,
                    "batch_id": "e5aed7fe-b649-43b0-9c2b-1cdeb315f724",
                    "is_a_batched_report": True,
                },
            ],
            [
                "Report Status",
                "Today 1,234 unsubscribe requests Downloaded",
                "Yesterday 4,567 unsubscribe requests Downloaded",
                "20 June 7,890 unsubscribe requests Downloaded",
            ],
        ),
        (
            # Three reports on the same day
            [
                {
                    "count": 1234,
                    "earliest_timestamp": "2024-06-01 21:22",
                    "latest_timestamp": "2024-06-01 22:00",
                    "processed_by_service_at": None,
                    "batch_id": "af5f5e86-528b-475e-8be1-012988987775",
                    "is_a_batched_report": True,
                },
                {
                    "count": 4567,
                    "earliest_timestamp": "2024-06-01 12:17",
                    "latest_timestamp": "2024-06-01 12:18",
                    "processed_by_service_at": None,
                    "batch_id": "c2d11916-ee82-419e-99a8-7e38163e756f",
                    "is_a_batched_report": True,
                },
                {
                    "count": 7890,
                    "earliest_timestamp": "2024-06-01 08:00",
                    "latest_timestamp": "2024-06-01 10:00",
                    "processed_by_service_at": None,
                    "batch_id": "e5aed7fe-b649-43b0-9c2b-1cdeb315f724",
                    "is_a_batched_report": True,
                },
            ],
            [
                "Report Status",
                "1 June at 11:22pm to 1 June at midnight 1,234 unsubscribe requests Downloaded",
                "1 June at 2:17pm to 1 June at 2:18pm 4,567 unsubscribe requests Downloaded",
                "1 June until midday 7,890 unsubscribe requests Downloaded",
            ],
        ),
    ),
)
@freeze_time("2024-06-22 22:22:22")
def test_unsubscribe_request_reports_summary(client_request, mocker, test_data, expected_rows):
    mocker.patch.object(UnsubscribeRequestsReports, "client_method", return_value=test_data)

    page = client_request.get("main.unsubscribe_request_reports_summary", service_id=SERVICE_ONE_ID)

    assert [normalize_spaces(row.text) for row in page.select("tr")] == expected_rows


def test_no_unsubscribe_request_reports_summary_to_display(client_request, mocker):

    mocker.patch.object(UnsubscribeRequestsReports, "client_method", return_value=[])

    page = client_request.get("main.unsubscribe_request_reports_summary", service_id=SERVICE_ONE_ID)

    assert ["Report Status", "If you have any email unsubscribe requests they will be listed here"] == [
        normalize_spaces(row.text) for row in page.select("tr")
    ]


@freeze_time("2024-06-22")
def test_unsubscribe_request_report_for_unprocessed_batched_reports(client_request, mocker):
    test_data = [
        {
            "count": 200,
            "earliest_timestamp": "2024-06-15",
            "latest_timestamp": "2024-06-21",
            "processed_by_service_at": None,
            "batch_id": "a8a526f9-84be-44a6-b751-62c95c4b9329",
            "is_a_batched_report": True,
        }
    ]

    mocker.patch.object(UnsubscribeRequestsReports, "client_method", return_value=test_data)

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
    assert "disabled" not in checkbox
    assert normalize_spaces(checkbox_hint) == "I have unsubscribed these recipients from our mailing list"
    assert normalize_spaces(unsubscribe_requests_count_text) == "200 new requests to unsubscribe"
    assert len(update_button) == 1
    assert normalize_spaces(availability_date) == "(available until 19 September 2024)"


@freeze_time("2024-07-02")
def test_unsubscribe_request_report_for_unbatched_reports(client_request, mocker):
    test_data = [
        {
            "count": 34,
            "earliest_timestamp": "2024-06-22 10:00",
            "latest_timestamp": "2024-07-01 12:00",
            "processed_by_service_at": None,
            "batch_id": None,
            "is_a_batched_report": False,
        }
    ]

    mocker.patch.object(UnsubscribeRequestsReports, "client_method", return_value=test_data)
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
    assert "disabled" in checkbox
    assert normalize_spaces(checkbox_hint) == "You cannot do this until you’ve downloaded the report"
    assert normalize_spaces(unsubscribe_requests_count_text) == "34 new requests to unsubscribe"
    assert normalize_spaces(availability_date) == "(available until 29 September 2024)"
    assert len(update_button) == 0


@freeze_time("2024-01-01")
def test_unsubscribe_request_report_for_processed_batched_reports(client_request, mocker):
    test_data = [
        {
            "count": 321,
            "earliest_timestamp": "2023-06-8",
            "latest_timestamp": "2023-06-14",
            "processed_by_service_at": "2024-06-10",
            "batch_id": "e5aed7fe-b649-43b0-9c2b-1cdeb315f724",
            "is_a_batched_report": True,
        },
    ]
    mocker.patch.object(UnsubscribeRequestsReports, "client_method", return_value=test_data)
    page = client_request.get(
        "main.unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=test_data[0]["batch_id"],
    )
    assert page.select("h1")[0].text == "8 June 2023 to 14 June 2023"
    checkbox = page.select("#report_has_been_processed")[0].attrs
    checkbox_hint = page.select("#report_has_been_processed-item-hint")[0].text
    main_body_text = page.select("#completed_unsubscribe_report_main_text")[0].text
    availability_date = page.select("#completed_unsubscribe_report_availability")[0].text
    "completed_unsubscribe_report_main_text"
    update_button = page.select("#process_unsubscribe_report")
    assert "disabled" not in checkbox
    assert "checked" in checkbox
    assert normalize_spaces(checkbox_hint) == "I have unsubscribed these recipients from our mailing list"
    assert normalize_spaces(main_body_text) == "Report was marked as completed on 10 June 2024"
    assert normalize_spaces(availability_date) == "(available until 17 June 2024)"
    assert len(update_button) == 1


@pytest.mark.parametrize("batch_id", ["32b4e359-d4df-49b6-a92b-2eaa9343cfdd", None])
def test_non_existing_unsubscribe_request_report_batch_id_returns_404(client_request, mocker, batch_id):

    mocker.patch.object(UnsubscribeRequestsReports, "client_method", return_value=[])
    page = client_request.get(
        "main.unsubscribe_request_report",
        _expected_status=404,
        service_id=SERVICE_ONE_ID,
        batch_id=batch_id,
    )
    assert normalize_spaces(page.select("h1")[0].text) == "Page not found"


def test_download_unsubscribe_request_report_redirects_to_batch_unsubscribe_request_report_endpoint_no_batch_id(
    client_request,
):
    client_request.get_response(
        "main.download_unsubscribe_request_report", service_id=SERVICE_ONE_ID, batch_id=None, _expected_status=302
    )


def test_create_unsubscribe_request_report_creates_batched_report(client_request, mocker):
    summary_data = [
        {
            "count": 34,
            "earliest_timestamp": "2024-06-22",
            "latest_timestamp": "2024-07-01",
            "processed_by_service_at": None,
            "batch_id": None,
            "is_a_batched_report": False,
        }
    ]
    test_batch_id = "daaa3f82-faf0-4199-82da-15ec6aa8abe8"
    mocker.patch.object(UnsubscribeRequestsReports, "client_method", return_value=summary_data)
    mock_batch_report = mocker.patch.object(
        service_api_client, "create_unsubscribe_request_report", return_value={"batch_id": test_batch_id}
    )
    client_request.get_response(
        "main.create_unsubscribe_request_report", service_id=SERVICE_ONE_ID, batch_id=None, _expected_status=302
    )
    mock_batch_report.assert_called_once_with(
        SERVICE_ONE_ID,
        {
            "count": 34,
            "earliest_timestamp": "2024-06-22",
            "latest_timestamp": "2024-07-01",
            "processed_by_service_at": None,
        },
    )
