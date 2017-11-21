import pytest

from tests.conftest import set_config_values


@pytest.mark.parametrize('check_proxy_header,header_value,expected_code', [
    (True, 'key_1', 200),
    (True, 'wrong_key', 403),
    (False, 'wrong_key', 200),
    (False, 'key_1', 200),
])
def test_route_correct_secret_key(app_, check_proxy_header, header_value, expected_code):
    with set_config_values(app_, {
        'ROUTE_SECRET_KEY_1': 'key_1',
        'ROUTE_SECRET_KEY_2': '',
        'CHECK_PROXY_HEADER': check_proxy_header,
    }):

        with app_.test_client() as client:
            response = client.get(
                path='/_status?elb=True',
                headers=[
                    ('X-Custom-forwarder', header_value),
                ]
            )
        assert response.status_code == expected_code
