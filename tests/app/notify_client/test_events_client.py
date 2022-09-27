from app.notify_client.events_api_client import EventsApiClient


def test_events_client_calls_correct_api_endpoint(mocker):

    expected_url = "/events"
    event_type = "anything"
    event_data = {"does_not": "matter"}
    expected_data = {"event_type": event_type, "data": event_data}

    client = EventsApiClient()

    mock_post = mocker.patch("app.notify_client.events_api_client.EventsApiClient.post")

    client.create_event(event_type, event_data)

    mock_post.assert_called_once_with(url=expected_url, data=expected_data)
