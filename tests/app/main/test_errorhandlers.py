from bs4 import BeautifulSoup
from flask import url_for


def test_bad_url_returns_page_not_found(app_):
    with app_.test_client() as client:
        response = client.get('/bad_url')
        assert response.status_code == 404
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.h1.string.strip() == 'Page could not be found'


def test_bad_input_returns_something(app_, api_user_active, mock_login):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.service_dashboard', service_id=1))
            response.status == 404
            print(response.get_data(as_text=True))
            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            assert page.h1.string.strip() == 'Page could not be found'
