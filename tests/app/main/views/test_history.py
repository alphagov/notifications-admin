from tests.conftest import SERVICE_ONE_ID, normalize_spaces


def test_history(
    client_request,
    mock_get_service_history,
):
    page = client_request.get('main.history', service_id=SERVICE_ONE_ID)

    assert page.select_one('h1').text == 'Service and API key history'

    headings = page.select('main h2')
    events = page.select('main ul')

    assert len(headings) == len(events)
    assert [
        (
            normalize_spaces(headings[index].text),
            normalize_spaces(events[index].text),
        ) for index in range(len(headings))
    ] == [
        (
            '12 December',
            (
                '6ce466d0-fd6a-11e5-82f5-e0accb9d11a6 12:12pm '
                'Renamed this service from ‘Example service’ to ‘Real service’'
            ),
        ),
        (
            '11 November',
            (
                '6ce466d0-fd6a-11e5-82f5-e0accb9d11a6 12:12pm '
                'Revoked the ‘Bad key’ API key'
            ),
        ),
        (
            '11 November',
            (
                '6ce466d0-fd6a-11e5-82f5-e0accb9d11a6 11:11am '
                'Created an API key called ‘Bad key’'
            ),
        ),
        (
            '10 October',
            (
                '6ce466d0-fd6a-11e5-82f5-e0accb9d11a6 11:10am '
                'Created this service and called it ‘Example service’ '
                '6ce466d0-fd6a-11e5-82f5-e0accb9d11a6 11:10am '
                'Created an API key called ‘Good key’'
            ),
        ),
    ]
