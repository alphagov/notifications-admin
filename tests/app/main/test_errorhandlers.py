from flask import Response
from bs4 import BeautifulSoup
from notifications_python_client.errors import HTTPError


def test_bad_url_returns_page_not_found(client):
    response = client.get('/bad_url')
    assert response.status_code == 404
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == 'Page could not be found'


def test_load_service_before_request_handles_404(client_request, mocker):
    exc = HTTPError(Response(status=404), 'Not found')
    get_service = mocker.patch('app.service_api_client.get_service', side_effect=exc)

    client_request.get(
        'main.service_dashboard',
        service_id='00000000-0000-0000-0000-000000000000',
        _expected_status=404
    )

    get_service.assert_called_once_with('00000000-0000-0000-0000-000000000000')
