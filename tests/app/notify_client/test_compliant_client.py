from app import ComplaintApiClient


def test_get_all_complaints(mocker):
    client = ComplaintApiClient()

    mock = mocker.patch('app.notify_client.complaint_api_client.ComplaintApiClient.get')

    client.get_all_complaints()
    mock.assert_called_once_with('/complaint')
