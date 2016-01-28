from tests import create_test_user
from flask import url_for
import pytest


def test_should_show_choose_services_page(app_,
                                          mock_get_user,
                                          api_user_active,
                                          mock_get_services,
                                          mock_login):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.choose_service'))

        assert response.status_code == 200
        resp_data = response.get_data(as_text=True)
        assert 'Choose service' in resp_data
        services = mock_get_services.side_effect()
        assert mock_get_services.called
        assert services['data'][0]['name'] in resp_data
        assert services['data'][1]['name'] in resp_data
