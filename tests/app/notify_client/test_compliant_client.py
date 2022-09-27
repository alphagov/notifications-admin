from app.notify_client.complaint_api_client import ComplaintApiClient


def test_get_all_complaints(mocker):
    client = ComplaintApiClient()

    mock = mocker.patch("app.notify_client.complaint_api_client.ComplaintApiClient.get")

    client.get_all_complaints()
    mock.assert_called_once_with("/complaint", params={"page": 1})


def test_get_all_complaints_with_a_page_number_specified(mocker):
    client = ComplaintApiClient()

    mock = mocker.patch("app.notify_client.complaint_api_client.ComplaintApiClient.get")

    client.get_all_complaints(page=3)
    mock.assert_called_once_with("/complaint", params={"page": 3})


def test_get_complaint_count(mocker):
    client = ComplaintApiClient()
    mock = mocker.patch.object(client, "get")
    params_dict = {"start_date": "2018-06-01", "end_date": "2018-06-15"}

    client.get_complaint_count(params_dict=params_dict)
    mock.assert_called_once_with("/complaint/count-by-date-range", params=params_dict)
