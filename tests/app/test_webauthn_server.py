import pytest

from app import webauthn_server


@pytest.mark.parametrize(('environment, allowed'), [
    ('development', True),
    ('production', False)
])
def test_server_origin_verification(
    app_,
    mocker,
    environment,
    allowed
):
    mocker.patch.dict(
        app_.config,
        values={'NOTIFY_ENVIRONMENT': environment}
    )

    webauthn_server.init_app(app_)
    assert app_.webauthn_server._verify('fake-domain') == allowed


def test_server_relying_party_id(
    app_,
    mocker,
):
    mocker.patch.dict(
        app_.config,
        values={'ADMIN_BASE_URL': 'https://www.notify.works'}
    )

    webauthn_server.init_app(app_)
    assert app_.webauthn_server.rp.id == 'www.notify.works'
