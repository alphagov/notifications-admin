import pytest

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


def test_unsubscribe_request_report_for_batched_reports(client_request, mocker):
    test_data = [
        {
            "count": 200,
            "earliest_timestamp": "2024-06-15",
            "latest_timestamp": "2024-06-21",
            "processed_by_service_at": None,
            "batch_id": "a8a526f9-84be-44a6-b751-62c95c4b9329",
            "is_a_batched_report": True,
        },
        {
            "count": 321,
            "earliest_timestamp": "2024-06-8",
            "latest_timestamp": "2024-06-14",
            "processed_by_service_at": "2024-06-10",
            "batch_id": "b9c28b5b-e442-4e5f-a9c7-c2544502627a",
            "is_a_batched_report": True,
        },
    ]

    mocker.patch.object(UnsubscribeRequestsReports, "client_method", return_value=test_data)

    page = client_request.get(
        "main.unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=test_data[1]["batch_id"],
    )
    assert page.select("h1")[0].text == "8 June 2024 until 14 June 2024"


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
    assert page.select("h1")[0].text == "22 June 2024 until 1 July 2024"


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


def test_unsubscribe_request_report_checkbox_for_completed_reports_are_checked_by_default(client_request, mocker):
    test_data = [
        {
            "count": 321,
            "earliest_timestamp": "2024-06-8",
            "latest_timestamp": "2024-06-14",
            "processed_by_service_at": None,
            "batch_id": "b9c28b5b-e442-4e5f-a9c7-c2544502627a",
            "is_a_batched_report": True,
        },
    ]

    mocker.patch.object(UnsubscribeRequestsReports, "client_method", return_value=test_data)
    page = client_request.get(
        "main.unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=test_data[0]["batch_id"],
    )
    assert "checked" in page.select("#report_has_been_processed")[0].attrs


def test_unsubscribe_request_report_checkbox_for_unbatched_reports_are_disabled_checked_by_default(
        client_request, mocker):
    test_data = [
        {
            "count": 34,
            "earliest_timestamp": "2024-06-22",
            "latest_timestamp": "2024-07-01",
            "processed_by_service_at": None,
            "batch_id": None,
            "is_a_batched_report": False,
        },
    ]

    mocker.patch.object(UnsubscribeRequestsReports, "client_method", return_value=test_data)
    page = client_request.get(
        "main.unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        batch_id=test_data[0]["batch_id"],
    )
    assert "disabled" in page.select("#report_has_been_processed")[0].attrs
