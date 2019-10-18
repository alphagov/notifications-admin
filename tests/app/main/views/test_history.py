from tests.conftest import SERVICE_ONE_ID, normalize_spaces


def test_history(
    client_request,
    mock_get_service_history,
):
    page = client_request.get('main.history', service_id=SERVICE_ONE_ID)

    assert normalize_spaces(
        page.select_one('main').text
    ) == (
        'Service and API key history '
        '11 November at 12:12pm 6ce466d0-fd6a-11e5-82f5-e0accb9d11a6'
        ' Revoked the ‘Bad key’ API key '
        '11 November at 11:11am 6ce466d0-fd6a-11e5-82f5-e0accb9d11a6'
        ' Created an API key called ‘Bad key’ '
        '10 October at 11:10am 6ce466d0-fd6a-11e5-82f5-e0accb9d11a6'
        ' Created an API key called ‘Good key’ '
        '10 October at 11:10am 6ce466d0-fd6a-11e5-82f5-e0accb9d11a6'
        ' Created this service and called it ‘Example service’'
    )
