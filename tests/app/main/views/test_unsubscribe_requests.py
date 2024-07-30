import pytest

from app import service_api_client
from app.models.unsubscribe_requests_report import UnsubscribeRequestsReports
from tests.conftest import SERVICE_ONE_ID, normalize_spaces


def test_unsubscribe_request_reports_summary(client_request, mocker):
    test_data = [
        {
            "count": 34,
            "earliest_timestamp": "2024-06-22",
            "latest_timestamp": "2024-07-01",
            "processed_by_service_at": None,
            "batch_id": "5e2b05ef-7552-49ef-a77f-96d46ab2b9bb",
            "is_a_batched_report": False,
        },
        {
            "count": 200,
            "earliest_timestamp": "2024-06-15",
            "latest_timestamp": "2024-06-21",
            "processed_by_service_at": None,
            "batch_id": "c2d11916-ee82-419e-99a8-7e38163e756f",
            "is_a_batched_report": True,
        },
        {
            "count": 321,
            "earliest_timestamp": "2024-06-8",
            "latest_timestamp": "2024-06-14",
            "processed_by_service_at": "2024-06-10",
            "batch_id": "e5aed7fe-b649-43b0-9c2b-1cdeb315f724",
            "is_a_batched_report": True,
        },
    ]
    mocker.patch.object(UnsubscribeRequestsReports, "client_method", return_value=test_data)

    page = client_request.get("main.unsubscribe_request_reports_summary", service_id=SERVICE_ONE_ID)

    assert [
        "Report Status",
        "22 June 2024 to 1 July 2024 34 unsubscribe requests Not downloaded",
        "15 June 2024 to 21 June 2024 200 unsubscribe requests Downloaded",
        "8 June 2024 to 14 June 2024 321 unsubscribe requests Completed",
    ] == [normalize_spaces(row.text) for row in page.select("tr")]


def test_no_unsubscribe_request_reports_summary_to_display(client_request, mocker):

    mocker.patch.object(UnsubscribeRequestsReports, "client_method", return_value=[])

    page = client_request.get("main.unsubscribe_request_reports_summary", service_id=SERVICE_ONE_ID)

    assert ["Report Status", "If you have any email unsubscribe requests they will be listed here"] == [
        normalize_spaces(row.text) for row in page.select("tr")
    ]


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
    assert page.select("h1")[0].text == "15 June 2024 until 21 June 2024"
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


def test_unsubscribe_request_report_for_unbatched_reports(client_request, mocker):
    test_data = [
        {
            "count": 34,
            "earliest_timestamp": "2024-06-22",
            "latest_timestamp": "2024-07-01",
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
    assert page.select("h1")[0].text == "22 June 2024 until 1 July 2024"
    assert "disabled" in checkbox
    assert normalize_spaces(checkbox_hint) == "You cannot do this until you've downloaded the report"
    assert normalize_spaces(unsubscribe_requests_count_text) == "34 new requests to unsubscribe"
    assert normalize_spaces(availability_date) == "(available until 29 September 2024)"
    assert len(update_button) == 0


def test_unsubscribe_request_report_for_processed_batched_reports(client_request, mocker):
    test_data = [
        {
            "count": 321,
            "earliest_timestamp": "2024-06-8",
            "latest_timestamp": "2024-06-14",
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
    assert page.select("h1")[0].text == "8 June 2024 until 14 June 2024"
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


def test_download_unsubscribe_request_report(client_request, mocker):
    report_data = {
        "batch_id": "3d466625-6ea4-414f-ac48-add30d895c43",
        "earliest_timestamp": "2024-07-01",
        "latest_timestamp": "2024-07-17",
        "unsubscribe_requests": [
            {
                "email_address": "fizz@bar.com",
                "template_name": "Template Fizz",
                "original_file_name": "Contact List 2",
                "template_sent_at": "2024-06-28",
            },
            {
                "email_address": "fizzbuzz@bar.com",
                "template_name": "Template FizzBuzz",
                "original_file_name": None,
                "template_sent_at": "2024-06-30",
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
        report.strip() == "Email address,Template name,Contact list file name,Template sent at\r\n"
        "fizz@bar.com,Template Fizz,Contact List 2,2024-06-28\r\n"
        "fizzbuzz@bar.com,Template FizzBuzz,,2024-06-30"
    )
