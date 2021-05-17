import pytest

from app import webauthn_server


@pytest.fixture
def app_with_mock_config(mocker):
    app = mocker.Mock()

    app.config = {
        'ADMIN_BASE_URL': 'https://www.notify.works',
        'NOTIFY_ENVIRONMENT': 'development'
    }

    return app


@pytest.mark.parametrize(('environment, allowed'), [
    ('development', True),
    ('production', False)
])
def test_server_origin_verification(
    app_with_mock_config,
    environment,
    allowed
):

    app_with_mock_config.config['NOTIFY_ENVIRONMENT'] = environment
    webauthn_server.init_app(app_with_mock_config)
    assert app_with_mock_config.webauthn_server._verify('fake-domain') == allowed


def test_server_relying_party_id(
    app_with_mock_config,
    mocker,
):
    webauthn_server.init_app(app_with_mock_config)
    assert app_with_mock_config.webauthn_server.rp.id == 'www.notify.works'
