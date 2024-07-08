from tests.conftest import SERVICE_ONE_ID, normalize_spaces


def test_unsubscribe_request_reports_summary(client_request, mocker):
    test_data = [
        {
            "count": 34,
            "earliest_timestamp": "2024-06-22",
            "latest_timestamp": "2024-07-01",
            "processed_by_service_at": None,
            "report_id": "5e2b05ef-7552-49ef-a77f-96d46ab2b9bb",
            "is_a_batched_report": False,
        },
        {
            "count": 200,
            "earliest_timestamp": "2024-06-15",
            "latest_timestamp": "2024-06-21",
            "processed_by_service_at": None,
            "report_id": "971bdf41-632c-4fdb-a84f-c5fb1b5d40b3",
            "is_a_batched_report": True,
        },
        {
            "count": 321,
            "earliest_timestamp": "2024-06-8",
            "latest_timestamp": "2024-06-14",
            "processed_by_service_at": "2024-06-10",
            "report_id": "368a9f4f-c425-4097-bae7-6d0a4de0f527",
            "is_a_batched_report": True,
        },
    ]
    mocker.patch("app.service_api_client.get_unsubscribe_reports_summary", return_value=test_data)

    page = client_request.get("main.unsubscribe_request_reports_summary", service_id=SERVICE_ONE_ID)

    assert [
        "Report",
        "22 June 2024 to 1 July 2024 34 unsubscribe requests Not Downloaded",
        "15 June 2024 to 21 June 2024 200 unsubscribe requests Downloaded",
        "8 June 2024 to 14 June 2024 321 unsubscribe requests Completed",
    ] == [normalize_spaces(row.text) for row in page.select("tr")]
