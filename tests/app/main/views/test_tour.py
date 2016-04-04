import pytest
from flask import url_for

import app


@pytest.mark.parametrize("page", range(1, 5))
def test_should_render_tour_pages(
    app_,
    api_user_active,
    mocker,
    page
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active, mocker)
            response = client.get(url_for('main.tour', service_id=101, page=page))
            assert response.status_code == 200
            assert 'Next' in response.get_data(as_text=True)
