import base64
from unittest.mock import ANY, Mock

import pytest
from fido2 import cbor
from flask import url_for

from app.models.webauthn_credential import RegistrationError, WebAuthnCredential


@pytest.fixture
def webauthn_authentication_post_data(fake_uuid, webauthn_credential, client):
    """
    Sets up session, challenge, etc as if a user with uuid `fake_uuid` has logged in and touched the webauthn token
    as found in the `webauthn_credential` fixture. Sets up the session as if `begin_authentication` had been called
    so that the challenge matches and the credential will validate (provided that the key belongs to the user referenced
    in the session).
    """
    with client.session_transaction() as session:
        session['user_details'] = {'id': fake_uuid}
        session['webauthn_authentication_state'] = {
            "challenge": "e-g-nXaRxMagEiqTJSyD82RsEc5if_6jyfJDy8bNKlw",
            "user_verification": None
        }

    credential_id = WebAuthnCredential(webauthn_credential).to_credential_data().credential_id

    return cbor.encode({
        'credentialId': credential_id,
        'authenticatorData': base64.b64decode(b'dKbqkhPJnC90siSSsyDPQCYqlMGpUKA5fyklC2CEHvABAAACfQ=='),
        'clientDataJSON': b'{"challenge":"e-g-nXaRxMagEiqTJSyD82RsEc5if_6jyfJDy8bNKlw","origin":"https://webauthn.io","type":"webauthn.get"}',  # noqa
        'signature': bytes.fromhex('304502204a76f05cd52a778cdd4df1565e0004e5cc1ead360419d0f5c3a0143bf37e7f15022100932b5c308a560cfe4f244214843075b904b3eda64e85d64662a81198c386cdde'),  # noqa
    })


def test_begin_register_forbidden_unless_can_use_webauthn(
    client_request,
    platform_admin_user,
    mocker,
):
    platform_admin_user['can_use_webauthn'] = False
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    client_request.get('main.webauthn_begin_register', _expected_status=403)


def test_begin_register_returns_encoded_options(
    mocker,
    platform_admin_user,
    client_request,
    webauthn_dev_server,
):
    mocker.patch('app.models.webauthn_credential.WebAuthnCredentials.client_method', return_value=[])

    client_request.login(platform_admin_user)
    response = client_request.get_response(
        'main.webauthn_begin_register',
    )

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
    assert relying_party_options['id'] == 'webauthn.io'


def test_begin_register_includes_existing_credentials(
    client_request,
    platform_admin_user,
    webauthn_credential,
    mocker,
):
    mocker.patch(
        'app.models.webauthn_credential.WebAuthnCredentials.client_method',
        return_value=[webauthn_credential, webauthn_credential]
    )

    client_request.login(platform_admin_user)
    response = client_request.get_response(
        'main.webauthn_begin_register',
    )

    webauthn_options = cbor.decode(response.data)['publicKey']
    assert len(webauthn_options['excludeCredentials']) == 2


def test_begin_register_stores_state_in_session(
    client_request,
    platform_admin_user,
    mocker,
):
    mocker.patch(
        'app.models.webauthn_credential.WebAuthnCredentials.client_method',
        return_value=[])

    client_request.login(platform_admin_user)
    client_request.get_response(
        'main.webauthn_begin_register',
    )

    with client_request.session_transaction() as session:
        assert session['webauthn_registration_state'] is not None


def test_complete_register_creates_credential(
    platform_admin_user,
    client_request,
    mock_update_user_attribute,
    mocker,
):
    with client_request.session_transaction() as session:
        session['webauthn_registration_state'] = 'state'

    user_api_mock = mocker.patch(
        'app.user_api_client.create_webauthn_credential_for_user'
    )

    credential_mock = mocker.patch(
        'app.models.webauthn_credential.WebAuthnCredential.from_registration',
        return_value='cred'
    )

    client_request.login(platform_admin_user)
    client_request.post_response(
        'main.webauthn_begin_register',
        _data=cbor.encode('public_key_credential'),
        _expected_status=200,
    )

    credential_mock.assert_called_once_with('state', 'public_key_credential')
    user_api_mock.assert_called_once_with(platform_admin_user['id'], 'cred')
    mock_update_user_attribute.assert_called_once_with(
        platform_admin_user['id'],
        auth_type='webauthn_auth',
    )


def test_complete_register_clears_session(
    client_request,
    platform_admin_user,
    mocker,
):
    with client_request.session_transaction() as session:
        session['webauthn_registration_state'] = 'state'

    mocker.patch('app.user_api_client.create_webauthn_credential_for_user')
    mocker.patch('app.models.webauthn_credential.WebAuthnCredential.from_registration')

    client_request.login(platform_admin_user)
    client_request.post(
        'main.webauthn_complete_register',
        _data=cbor.encode('public_key_credential'),
        _expected_status=200,
    )

    with client_request.session_transaction() as session:
        assert 'webauthn_registration_state' not in session
        assert session['_flashes'] == [('default_with_tick', (
            'Registration complete. Next time you sign in to Notify '
            'you’ll be asked to use your security key.'
        ))]


def test_complete_register_handles_library_errors(
    client_request,
    platform_admin_user,
    mocker,
):
    with client_request.session_transaction() as session:
        session['webauthn_registration_state'] = 'state'

    mocker.patch(
        'app.models.webauthn_credential.WebAuthnCredential.from_registration',
        side_effect=RegistrationError('error')
    )

    client_request.login(platform_admin_user)
    client_request.post_response(
        'main.webauthn_complete_register',
        _data=cbor.encode('public_key_credential'),
        _expected_status=400,
    )


def test_complete_register_handles_missing_state(
    client_request,
    platform_admin_user,
    mocker,
):
    client_request.login(platform_admin_user)
    response = client_request.post_response(
        'main.webauthn_complete_register',
        _data=cbor.encode('public_key_credential'),
        _expected_status=400,
    )

    assert cbor.decode(response.data) == 'No registration in progress'


def test_begin_authentication_forbidden_for_users_without_webauthn(client, mocker, platform_admin_user):
    platform_admin_user['auth_type'] = 'sms_auth'
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)

    with client.session_transaction() as session:
        session['user_details'] = {'id': '1'}

    response = client.get(url_for('main.webauthn_begin_authentication'))
    assert response.status_code == 403


def test_begin_authentication_returns_encoded_options(client, mocker, webauthn_credential, platform_admin_user):
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)

    with client.session_transaction() as session:
        session['user_details'] = {'id': platform_admin_user['id']}

    get_creds_mock = mocker.patch(
        'app.models.webauthn_credential.WebAuthnCredentials.client_method',
        return_value=[webauthn_credential]
    )
    response = client.get(url_for('main.webauthn_begin_authentication'))

    decoded_data = cbor.decode(response.data)
    allowed_credentials = decoded_data['publicKey']['allowCredentials']

    assert len(allowed_credentials) == 1
    assert decoded_data['publicKey']['timeout'] == 30000
    get_creds_mock.assert_called_once_with(platform_admin_user['id'])


def test_begin_authentication_stores_state_in_session(client, mocker, webauthn_credential, platform_admin_user):
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)

    with client.session_transaction() as session:
        session['user_details'] = {'id': platform_admin_user['id']}

    mocker.patch(
        'app.models.webauthn_credential.WebAuthnCredentials.client_method',
        return_value=[webauthn_credential]
    )
    client.get(url_for('main.webauthn_begin_authentication'))

    with client.session_transaction() as session:
        assert 'challenge' in session['webauthn_authentication_state']


def test_complete_authentication_checks_credentials(
    client,
    mocker,
    webauthn_credential,
    webauthn_dev_server,
    mock_create_event,
    webauthn_authentication_post_data,
    platform_admin_user
):
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    mocker.patch('app.models.webauthn_credential.WebAuthnCredentials.client_method', return_value=[webauthn_credential])
    mocker.patch(
        'app.main.views.webauthn_credentials._complete_webauthn_login_attempt',
        return_value=Mock(location='/foo')
    )

    response = client.post(url_for('main.webauthn_complete_authentication'), data=webauthn_authentication_post_data)

    assert response.status_code == 200
    assert cbor.decode(response.data) == {'redirect_url': '/foo'}


def test_complete_authentication_403s_if_key_isnt_in_users_credentials(
    client,
    mocker,
    webauthn_credential,
    webauthn_dev_server,
    webauthn_authentication_post_data,
    platform_admin_user
):
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    # user has no keys in the database
    mocker.patch('app.models.webauthn_credential.WebAuthnCredentials.client_method', return_value=[])
    mock_verify_webauthn_login = mocker.patch('app.main.views.webauthn_credentials._complete_webauthn_login_attempt')
    mock_unsuccesful_login_api_call = mocker.patch('app.user_api_client.complete_webauthn_login_attempt')

    response = client.post(url_for('main.webauthn_complete_authentication'), data=webauthn_authentication_post_data)
    assert response.status_code == 403

    with client.session_transaction() as session:
        assert session['user_details']['id'] == platform_admin_user['id']
        # user not logged in
        assert 'user_id' not in session
        # webauthn state reset so can't replay
        assert 'webauthn_authentication_state' not in session

    assert mock_verify_webauthn_login.called is False
    # make sure we incremented the failed login count
    mock_unsuccesful_login_api_call.assert_called_once_with(platform_admin_user['id'], False)


def test_complete_authentication_clears_session(
    client,
    mocker,
    webauthn_credential,
    webauthn_dev_server,
    webauthn_authentication_post_data,
    mock_create_event,
    platform_admin_user
):
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    mocker.patch('app.user_api_client.get_webauthn_credentials_for_user', return_value=[webauthn_credential])
    mocker.patch(
        'app.main.views.webauthn_credentials._complete_webauthn_login_attempt',
        return_value=Mock(location='/foo')
    )

    client.post(url_for('main.webauthn_complete_authentication'), data=webauthn_authentication_post_data)

    with client.session_transaction() as session:
        # it's important that we clear the session to ensure that we don't re-use old login artifacts in future
        assert 'webauthn_authentication_state' not in session


@pytest.mark.parametrize('url_kwargs, expected_redirect', [
    ({}, '/accounts-or-dashboard'),
    ({'next': '/bar'}, '/bar'),
])
def test_verify_webauthn_login_signs_user_in(
    client,
    mocker,
    mock_create_event,
    platform_admin_user,
    url_kwargs,
    expected_redirect,
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': platform_admin_user['id'],
            'email': platform_admin_user['email_address']
        }
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    mocker.patch('app.main.views.webauthn_credentials._verify_webauthn_authentication')
    mocker.patch('app.user_api_client.complete_webauthn_login_attempt', return_value=(True, None))
    mocker.patch('app.main.views.webauthn_credentials.email_needs_revalidating', return_value=False)

    resp = client.post(url_for('main.webauthn_complete_authentication', **url_kwargs))

    assert resp.status_code == 200
    assert cbor.decode(resp.data)['redirect_url'] == expected_redirect
    # removes stuff from session
    with client.session_transaction() as session:
        assert 'user_details' not in session

    mock_create_event.assert_called_once_with('sucessful_login', ANY)


def test_verify_webauthn_login_signs_user_in_doesnt_sign_user_in_if_api_rejects(
    client,
    mocker,
    platform_admin_user,
):

    with client.session_transaction() as session:
        session['user_details'] = {
            'id': platform_admin_user['id'],
            'email': platform_admin_user['email_address']
        }
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    mocker.patch('app.main.views.webauthn_credentials._verify_webauthn_authentication')
    mocker.patch('app.user_api_client.complete_webauthn_login_attempt', return_value=(False, None))

    resp = client.post(url_for('main.webauthn_complete_authentication'))

    assert resp.status_code == 403


def test_verify_webauthn_login_signs_user_in_sends_revalidation_email_if_needed(
    client,
    mocker,
    mock_send_verify_code,
    platform_admin_user,
):
    user_details = {
        'id': platform_admin_user['id'],
        'email': platform_admin_user['email_address']
    }

    with client.session_transaction() as session:
        session['user_details'] = user_details

    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    mocker.patch('app.main.views.webauthn_credentials._verify_webauthn_authentication')
    mocker.patch('app.user_api_client.complete_webauthn_login_attempt', return_value=(True, None))
    mocker.patch('app.main.views.webauthn_credentials.email_needs_revalidating', return_value=True)

    resp = client.post(url_for('main.webauthn_complete_authentication'))

    assert resp.status_code == 200
    assert cbor.decode(resp.data)['redirect_url'] == url_for('main.revalidate_email_sent')

    with client.session_transaction() as session:
        # stuff stays in session so we can log them in later when they validate their email
        assert session['user_details'] == user_details

    mock_send_verify_code.assert_called_once_with(platform_admin_user['id'], 'email', ANY, ANY)
