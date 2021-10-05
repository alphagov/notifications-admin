from fido2 import cbor
from fido2.client import ClientData
from fido2.ctap2 import AuthenticatorData
from flask import abort, current_app, flash, redirect, request, session, url_for
from flask_login import current_user

from app.main import main
from app.models.user import User
from app.models.webauthn_credential import RegistrationError, WebAuthnCredential
from app.notify_client.user_api_client import user_api_client
from app.utils.login import (
    email_needs_revalidating,
    log_in_user,
    redirect_to_sign_in,
)
from app.utils.user import user_is_logged_in


@main.route('/webauthn/register')
@user_is_logged_in
def webauthn_begin_register():
    if not current_user.can_use_webauthn:
        abort(403)

    server = current_app.webauthn_server

    registration_data, state = server.register_begin(
        {
            "id": bytes(current_user.id, 'utf-8'),
            "name": current_user.email_address,
            "displayName": current_user.name,
        },
        credentials=current_user.webauthn_credentials.as_cbor,
        user_verification="discouraged",  # don't ask for PIN
        authenticator_attachment="cross-platform",
    )

    session["webauthn_registration_state"] = state
    return cbor.encode(registration_data)


@main.route('/webauthn/register', methods=['POST'])
@user_is_logged_in
def webauthn_complete_register():
    if 'webauthn_registration_state' not in session:
        return cbor.encode("No registration in progress"), 400

    try:
        credential = WebAuthnCredential.from_registration(
            session.pop("webauthn_registration_state"),
            cbor.decode(request.get_data()),
        )
    except RegistrationError as e:
        current_app.logger.info(f'User {current_user.id} could not register a new webauthn token - {e}')
        abort(400)

    current_user.create_webauthn_credential(credential)
    current_user.update(auth_type='webauthn_auth')

    flash((
        'Registration complete. Next time you sign in to Notify '
        'you’ll be asked to use your security key.'
    ), 'default_with_tick')

    return cbor.encode('')


@main.route('/webauthn/authenticate', methods=['GET'])
@redirect_to_sign_in
def webauthn_begin_authentication():
    """
    Initiate the authentication flow. This is called after the user clicks the "Check security key" button.

    1. Get the user's credentials out of the database to present to the browser. The browser will only let you use a
    credential in that list.
    2. Call webauthn_server.authenticate_begin. This returns the authentication data, which includes the challenge and
    the origin domain to authenticate with. This also returns the state, which we store in the cookie so we can ensure
    the challenge is correct in webauthn_complete_authentication
    """
    # get user from session
    user_to_login = User.from_id(session['user_details']['id'])

    if not user_to_login.webauthn_auth:
        abort(403)

    authentication_data, state = current_app.webauthn_server.authenticate_begin(
        credentials=user_to_login.webauthn_credentials.as_cbor,
        user_verification="discouraged",  # don't ask for PIN
    )
    session["webauthn_authentication_state"] = state
    return cbor.encode(authentication_data)


@main.route('/webauthn/authenticate', methods=['POST'])
@redirect_to_sign_in
def webauthn_complete_authentication():
    """
    Complete the authentication flow. This is called after the user taps on their security key.

    1. Try verifying the signed challenge returned from the browser with each public key we have in the database for
    that user.
    2. If succesful, log the user in, setting up the session etc. Then return the URL they should be redirected to.
    """
    user_id = session['user_details']['id']
    user_to_login = User.from_id(user_id)

    _verify_webauthn_authentication(user_to_login)
    redirect = _complete_webauthn_login_attempt(user_to_login)

    return cbor.encode({'redirect_url': redirect.location}), 200


def _verify_webauthn_authentication(user):
    """
    Check that the presented security key is valid, has signed the right challenge, and belongs to the user
    we're trying to log in.
    """
    state = session.pop("webauthn_authentication_state")
    request_data = cbor.decode(request.get_data())

    try:
        current_app.webauthn_server.authenticate_complete(
            state=state,
            credentials=user.webauthn_credentials.as_cbor,
            credential_id=request_data['credentialId'],
            client_data=ClientData(request_data['clientDataJSON']),
            auth_data=AuthenticatorData(request_data['authenticatorData']),
            signature=request_data['signature']
        )
    except ValueError as exc:
        # We don't expect to reach this case in normal situations - normally errors (such as using the wrong
        # security key) will be caught in the browser inside `window.navigator.credentials.get`, and the js will
        # error first meaning it doesn't send the POST request to this method. If this method is called but the key
        # couldn't be authenticated, something went wrong along the way, probably:
        # * The browser didn't implement the webauthn standard correctly, and let something through it shouldn't have
        # * The key itself is in some way corrupted, or of lower security standard
        current_app.logger.info(f'User {user.id} could not sign in using their webauthn token - {exc}')
        user.complete_webauthn_login_attempt(is_successful=False)
        abort(403)


def _complete_webauthn_login_attempt(user):
    """
    * check the user hasn't gone over their max logins
    * check that the user's email is validated
    * if succesful, update current_session_id, log in date, and then redirect
    """
    redirect_url = request.args.get('next')

    # normally API handles this when verifying an sms or email code but since the webauthn logic happens in the
    # admin we need a separate call that just finalises the login in the database
    logged_in, _ = user.complete_webauthn_login_attempt()
    if not logged_in:
        # user account is locked as too many failed logins
        abort(403)

    if email_needs_revalidating(user):
        user_api_client.send_verify_code(user.id, 'email', None, redirect_url)
        return redirect(url_for('.revalidate_email_sent', next=redirect_url))

    return log_in_user(user.id)
