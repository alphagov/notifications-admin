from fido2 import cbor
from flask import current_app, request, session
from flask_login import current_user

from app.main import main
from app.models.webauthn_credential import WebAuthnCredential
from app.notify_client.user_api_client import user_api_client
from app.utils import user_is_platform_admin


@main.route('/webauthn/register')
@user_is_platform_admin
def webauthn_begin_register():
    server = current_app.webauthn_server

    registration_data, state = server.register_begin(
        {
            "id": bytes(current_user.id, 'utf-8'),
            "name": current_user.email_address,
            "displayName": current_user.name,
        },
        credentials=[
            credential.to_credential_data()
            for credential in current_user.webauthn_credentials
        ],
        user_verification="discouraged",  # don't ask for PIN
        authenticator_attachment="cross-platform",
    )

    session["webauthn_registration_state"] = state
    return cbor.encode(registration_data)


@main.route('/webauthn/register', methods=['POST'])
@user_is_platform_admin
def webauthn_complete_register():
    credential = WebAuthnCredential.from_registration(
        session.pop("webauthn_registration_state"),
        cbor.decode(request.get_data()),
    )

    user_api_client.create_webauthn_credential_for_user(
        current_user.id, credential
    )

    return ''
