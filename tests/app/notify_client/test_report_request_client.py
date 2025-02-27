from app.notify_client.report_request_api_client import ReportRequestClient


def test_client_gets_report_request_by_service_id_and_report_request_id(mocker):
    service_id = "1234"
    report_request_id = "abcd"
    mock_get = mocker.patch("app.notify_client.report_request_api_client.ReportRequestClient.get")

    client = ReportRequestClient(mocker.MagicMock())
    client.get_report_request(service_id, report_request_id)

    mock_get.assert_called_once_with(url=f"/service/{service_id}/report-request/{report_request_id}")
