from tests.conftest import SERVICE_ONE_ID


def test_history(
    client_request,
    mock_get_service_history,
):
    client_request.get('main.history', service_id=SERVICE_ONE_ID)
