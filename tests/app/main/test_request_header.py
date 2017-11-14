from tests.conftest import set_config_values


def test_route_correct_secret_key(app_, client):
    with set_config_values(app_, {
        'ROUTE_SECRET_KEY_1': 'key_1',
        'ROUTE_SECRET_KEY_2': '',
        'DEBUG': False,
    }):

        response = client.get(
            path='/_status',
            headers=[
                ('X-Custom-forwarder', 'key_1'),
            ]
        )
        assert response.status_code == 200


def test_route_incorrect_secret_key(app_, client):
    with set_config_values(app_, {
        'ROUTE_SECRET_KEY_1': 'key_1',
        'ROUTE_SECRET_KEY_2': '',
        'DEBUG': False,
    }):

        response = client.get(
            path='/_status',
            headers=[
                ('X-Custom-forwarder', 'wrong_key'),
            ]
        )
        assert response.status_code == 403
