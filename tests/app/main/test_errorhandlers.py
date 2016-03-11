from bs4 import BeautifulSoup
from flask import url_for


def test_bad_url_returns_page_not_found(app_):
    with app_.test_client() as client:
        response = client.get('/bad_url')
        assert response.status_code == 404
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.h1.string.strip() == 'Page could not be found'
