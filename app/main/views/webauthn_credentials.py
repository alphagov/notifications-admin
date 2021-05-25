from fido2 import cbor
from fido2.client import ClientData
from fido2.ctap2 import AuthenticatorData
from flask import abort, current_app, flash, redirect, request, session, url_for
from flask_login import current_user

from app.main import main
from app.main.views.two_factor import log_in_user
from app.models.user import User
from app.models.webauthn_credential import RegistrationError, WebAuthnCredential
from app.notify_client.user_api_client import user_api_client
from app.utils import (
    is_less_than_days_ago,
    redirect_to_sign_in,
    user_is_platform_admin,
)


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
    if 'webauthn_registration_state' not in session:
        return cbor.encode("No registration in progress"), 400

    try:
        credential = WebAuthnCredential.from_registration(
            session.pop("webauthn_registration_state"),
            cbor.decode(request.get_data()),
        )
    except RegistrationError as e:
        return cbor.encode(str(e)), 400

    user_api_client.create_webauthn_credential_for_user(
        current_user.id, credential
    )

    return cbor.encode('')


@main.route('/webauthn/authenticate', methods=['GET'])
@redirect_to_sign_in
def webauthn_begin_authentication():
    # get user from session
    user_to_login = User.from_id(session['user_details']['id'])

    if not user_to_login.webauthn_auth:
        abort(403)

    if not user_to_login.platform_admin:
        abort(403)

    authentication_data, state = current_app.webauthn_server.authenticate_begin(
        credentials=[
            credential.to_credential_data()
            for credential in user_to_login.webauthn_credentials
        ],
        user_verification=None,  # required, preferred, discouraged. sets whether to ask for PIN
    )
    session["webauthn_authentication_state"] = state
    return cbor.encode(authentication_data)


@main.route('/webauthn/authenticate', methods=['POST'])
@redirect_to_sign_in
def webauthn_complete_authentication():
    user_id = session['user_details']['id']
    user_to_login = User.from_id(user_id)

    if not user_to_login.webauthn_auth:
        abort(403)

    if not user_to_login.platform_admin:
        abort(403)

    _complete_webauthn_authentication(user_to_login)

    redirect = _verify_webauthn_login(user_to_login)
    return cbor.encode({'redirect_url': redirect.location}), 200


def _complete_webauthn_authentication(user):
    state = session.pop("webauthn_authentication_state")
    request_data = cbor.decode(request.get_data())

    try:
        current_app.webauthn_server.authenticate_complete(
            state=state,
            credentials=[
                credential.to_credential_data()
                for credential in user.webauthn_credentials
            ],
            credential_id=request_data['credentialId'],
            client_data=ClientData(request_data['clientDataJSON']),
            auth_data=AuthenticatorData(request_data['authenticatorData']),
            signature=request_data['signature']
        )
    except ValueError as exc:
        current_app.logger.info(f'User {user.id} could not sign in using their webauthn token - {exc}')
        flash('Security key not recognised')
        user.verify_webauthn_login(is_successful=False)
        abort(403)


def _verify_webauthn_login(user):
    """
    * check the user hasn't gone over their max logins
    * check that the user's email is validated
    * if succesful, update current_session_id, log in date, and then redirect

    """
    redirect_url = request.args.get('next')

    # normally API handles this when verifying an sms or email code but since the webauthn logic happens in the
    # admin we need a separate call that just finalises the login in the database
    logged_in, _ = user.verify_webauthn_login()
    if not logged_in:
        # user account is locked as too many failed logins
        flash('Security key not recognised')
        abort(403)

    if not is_less_than_days_ago(user.email_access_validated_at, 90):
        user_api_client.send_verify_code(user.id, 'email', None, redirect_url)
        return redirect(url_for('.revalidate_email_sent', next=redirect_url))

    return log_in_user(user.id)
