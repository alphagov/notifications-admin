from app.notify_client.report_request_api_client import ReportRequestClient


def test_client_gets_report_request_by_service_id_and_report_request_id(mocker):
    service_id = "1234"
    report_request_id = "abcd"
    mock_get = mocker.patch("app.notify_client.report_request_api_client.ReportRequestClient.get")

    client = ReportRequestClient(mocker.MagicMock())
    client.get_report_request(service_id, report_request_id)

    mock_get.assert_called_once_with(url=f"/service/{service_id}/report-request/{report_request_id}")


def test_create_report_request(mocker):
    service_id = "1234"
    report_type = "notifications_report"
    test_data = {"key": "value"}
    mock_post = mocker.patch("app.notify_client.report_request_api_client.ReportRequestClient.post")

    client = ReportRequestClient(mocker.MagicMock())
    report_id = client.create_report_request(service_id, report_type, test_data)

    mock_post.assert_called_once_with(
        url=f"/service/{service_id}/report-request?report_type={report_type}", data=test_data
    )
    assert report_id
