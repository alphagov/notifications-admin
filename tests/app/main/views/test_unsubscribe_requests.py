from tests.conftest import SERVICE_ONE_ID, normalize_spaces


def test_unsubscribe_request_reports_summary(client_request, mocker):
    test_data = {
        "batched_reports_summaries": [
            {
                "count": 200,
                "earliest_timestamp": "2024-06-15",
                "latest_timestamp": "2024-06-21",
                "processed_by_service_at": None,
                "report_id": "ab26e2bc-da34-4326-bc2e-d957c14edde6",
                "is_a_batched_report": True,
            },
            {
                "count": 321,
                "earliest_timestamp": "2024-06-8",
                "latest_timestamp": "2024-06-14",
                "processed_by_service_at": "2024-06-10",
                "report_id": "a46004d4-a4f5-4e9a-ad66-309fe503f7e6",
                "is_a_batched_report": True,
            },
        ],
        "unbatched_report_summary": {
            "count": 34,
            "earliest_timestamp": "2024-06-22",
            "latest_timestamp": "2024-07-01",
            "processed_by_service_at": None,
            "report_id": "5e2b05ef-7552-49ef-a77f-96d46ab2b9bb",
            "is_a_batched_report": False,
        },
    }
    mocker.patch("app.service_api_client.get_unsubscribe_reports_summary", return_value=test_data)

    page = client_request.get("main.unsubscribe_request_reports_summary", service_id=SERVICE_ONE_ID)

    assert [
        "Report",
        "22 June 2024 to 1 July 2024 34 unsubscribe requests Not Downloaded",
        "15 June 2024 to 21 June 2024 200 unsubscribe requests Downloaded",
        "8 June 2024 to 14 June 2024 321 unsubscribe requests Completed",
    ] == [normalize_spaces(row.text) for row in page.select("tr")]


def test_no_unsubscribe_request_reports_summary_to_display(client_request, mocker):
    test_data = {
        "batched_reports_summaries": [],
        "unbatched_report_summary": {},
    }
    mocker.patch("app.service_api_client.get_unsubscribe_reports_summary", return_value=test_data)

    page = client_request.get("main.unsubscribe_request_reports_summary", service_id=SERVICE_ONE_ID)

    assert ["Report", "If you have unsubscribed requests they will be listed here"] == [
        normalize_spaces(row.text) for row in page.select("tr")
    ]


def test_unsubscribe_request_report_for_existing_reports(client_request, mocker):
    test_data = test_data = {
        "batched_reports_summaries": [
            {
                "count": 200,
                "earliest_timestamp": "2024-06-15",
                "latest_timestamp": "2024-06-21",
                "processed_by_service_at": None,
                "report_id": "a8a526f9-84be-44a6-b751-62c95c4b9329",
                "is_a_batched_report": True,
            },
            {
                "count": 321,
                "earliest_timestamp": "2024-06-8",
                "latest_timestamp": "2024-06-14",
                "processed_by_service_at": "2024-06-10",
                "report_id": "b9c28b5b-e442-4e5f-a9c7-c2544502627a",
                "is_a_batched_report": True,
            },
        ],
        "unbatched_report_summary": {},
    }
    mocker.patch("app.service_api_client.get_unsubscribe_reports_summary", return_value=test_data)
    page = client_request.get(
        "main.unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        report_id=test_data["batched_reports_summaries"][1]["report_id"],
    )
    assert page.select("h1")[0].text == "8 June 2024 until 14 June 2024"


def test_unsubscribe_request_report_for_unbatched_reports(client_request, mocker):
    test_data = {
        "batched_reports_summaries": [],
        "unbatched_report_summary": {
            "count": 34,
            "earliest_timestamp": "2024-06-22",
            "latest_timestamp": "2024-07-01",
            "processed_by_service_at": None,
            "report_id": "efcab5ff-31e4-4aa0-ac23-9ecd862073be",
            "is_a_batched_report": False,
        },
    }
    mocker.patch("app.service_api_client.get_unsubscribe_reports_summary", return_value=test_data)
    page = client_request.get(
        "main.unsubscribe_request_report",
        service_id=SERVICE_ONE_ID,
        report_id=test_data["unbatched_report_summary"]["report_id"],
    )
    assert page.select("h1")[0].text == "22 June 2024 until 1 July 2024"
