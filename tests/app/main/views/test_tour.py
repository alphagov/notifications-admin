import pytest
from flask import url_for


@pytest.mark.parametrize("page", range(1, 5))
def test_should_render_tour_pages(
    app_,
    api_user_active,
    mocker,
    mock_get_service,
    page
):
    with app_.test_request_context():
        with app_.test_client() as client:
            response = client.get(url_for('main.tour', page=page))
            assert response.status_code == 200
            assert 'Next' in response.get_data(as_text=True)
