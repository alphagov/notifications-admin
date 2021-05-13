import pytest
from fido2 import cbor
from flask import url_for

from app import webauthn_server


@pytest.mark.parametrize('endpoint', [
    'webauthn_begin_register',
])
def test_register_forbidden_for_non_platform_admins(
    client_request,
    endpoint,
):
    client_request.get(f'main.{endpoint}', _expected_status=403)


def test_begin_register_returns_encoded_options(
    app_,
    mocker,
    platform_admin_user,
    platform_admin_client,
):
    # override base URL so it's consistent on CI and locally
    mocker.patch.dict(
        app_.config,
        values={'ADMIN_BASE_URL': 'http://localhost:6012'}
    )
    webauthn_server.init_app(app_)

    response = platform_admin_client.get(
        url_for('main.webauthn_begin_register')
    )

    assert response.status_code == 200

    webauthn_options = cbor.decode(response.data)['publicKey']
    assert webauthn_options['attestation'] == 'direct'
    assert webauthn_options['timeout'] == 30_000

    auth_selection = webauthn_options['authenticatorSelection']
    assert auth_selection['authenticatorAttachment'] == 'cross-platform'
    assert auth_selection['userVerification'] == 'discouraged'

    user_options = webauthn_options['user']
    assert user_options['name'] == platform_admin_user['email_address']
    assert user_options['id'] == bytes(platform_admin_user['id'], 'utf-8')

    relying_party_options = webauthn_options['rp']
    assert relying_party_options['name'] == 'GOV.UK Notify'
    assert relying_party_options['id'] == 'localhost'


def test_begin_register_includes_existing_credentials(
    platform_admin_client,
    webauthn_credential,
    mocker,
):
    mocker.patch(
        'app.user_api_client.get_webauthn_credentials_for_user',
        return_value=[webauthn_credential, webauthn_credential]
    )

    response = platform_admin_client.get(
        url_for('main.webauthn_begin_register')
    )

    webauthn_options = cbor.decode(response.data)['publicKey']
    assert len(webauthn_options['excludeCredentials']) == 2


def test_begin_register_stores_state_in_session(
    platform_admin_client,
):
    platform_admin_client.get(
        url_for('main.webauthn_begin_register')
    )

    with platform_admin_client.session_transaction() as session:
        assert session['webauthn_registration_state'] is not None


def test_complete_register_creates_credential(
    platform_admin_user,
    platform_admin_client,
    mocker,
):
    with platform_admin_client.session_transaction() as session:
        session['webauthn_registration_state'] = 'state'

    user_api_mock = mocker.patch(
        'app.user_api_client.create_webauthn_credential_for_user'
    )

    credential_mock = mocker.patch(
        'app.models.webauthn_credential.WebAuthnCredential.from_registration',
        return_value='cred'
    )

    response = platform_admin_client.post(
        url_for('main.webauthn_complete_register'),
        data=cbor.encode('public_key_credential'),
    )

    assert response.status_code == 200
    credential_mock.assert_called_once_with('state', 'public_key_credential')
    user_api_mock.assert_called_once_with(platform_admin_user['id'], 'cred')


def test_complete_register_clears_session(
    platform_admin_client,
    mocker,
):
    with platform_admin_client.session_transaction() as session:
        session['webauthn_registration_state'] = 'state'

    mocker.patch('app.user_api_client.create_webauthn_credential_for_user')
    mocker.patch('app.models.webauthn_credential.WebAuthnCredential.from_registration')

    platform_admin_client.post(
        url_for('main.webauthn_complete_register'),
        data=cbor.encode('public_key_credential'),
    )

    with platform_admin_client.session_transaction() as session:
        assert 'webauthn_registration_state' not in session
