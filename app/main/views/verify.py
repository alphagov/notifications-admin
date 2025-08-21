from flask import abort, current_app, flash, redirect, render_template, session, url_for
from itsdangerous import SignatureExpired
from notifications_utils.url_safe_token import check_token

from app import user_api_client
from app.constants import PERMISSION_CAN_MAKE_SERVICES_LIVE
from app.main import main
from app.main.forms import TwoFactorForm
from app.models.token import Token
from app.models.user import InvitedOrgUser, InvitedUser, User
from app.utils.login import redirect_to_sign_in


@main.route("/verify", methods=["GET", "POST"])
@redirect_to_sign_in
def verify():
    user_id = session["user_details"]["id"]

    def _check_code(code):
        return user_api_client.check_verify_code(user_id, code, "sms")

    form = TwoFactorForm(_check_code)

    if form.validate_on_submit():
        session.pop("user_details", None)
        return activate_user(user_id)

    return render_template("views/two-factor-sms.html", form=form, error_summary_enabled=True)


@main.route("/verify-email/<string:token>")
def verify_email(token):
    try:
        token_data = check_token(
            token,
            current_app.config["SECRET_KEY"],
            current_app.config["DANGEROUS_SALT"],
            current_app.config["EMAIL_EXPIRY_SECONDS"],
        )
    except SignatureExpired:
        flash("De link in de e-mail die we je hebben gestuurd is verlopen. We hebben je een nieuwe gestuurd.")
        return redirect(url_for("main.resend_email_verification"))

    token = Token(token_data)
    user = User.from_id(token.user_id)
    if not user:
        abort(404)

    if user.is_active:
        flash("Die verificatielink is verlopen.")
        return redirect(url_for("main.sign_in"))

    if user.email_auth:
        session.pop("user_details", None)
        return activate_user(user.id)

    user.send_verify_code()
    session["user_details"] = {"email": user.email_address, "id": user.id}
    return redirect(url_for("main.verify"))


def activate_user(user_id):
    user = User.from_id(user_id)
    # de gebruiker krijgt een nieuwe current_session_id toegekend door de API -
    # sla deze op in de cookie voor toekomstige verzoeken
    session["current_session_id"] = user.current_session_id
    organisation_id = session.get("organisation_id")
    activated_user = user.activate()
    activated_user.login()

    invited_user = InvitedUser.from_session()
    if invited_user:
        service_id = _add_invited_user_to_service(invited_user)
        return redirect(url_for("main.service_dashboard", service_id=service_id))

    invited_org_user = InvitedOrgUser.from_session()
    if invited_org_user:
        user_api_client.add_user_to_organisation(
            invited_org_user.organisation, user_id, permissions=[PERMISSION_CAN_MAKE_SERVICES_LIVE]
        )

    if organisation_id:
        return redirect(url_for("main.organisation_dashboard", org_id=organisation_id))

    if user.default_organisation.can_ask_to_join_a_service:
        return redirect(url_for("main.your_services"))

    return redirect(url_for("main.add_service"))


def _add_invited_user_to_service(invitation):
    user = User.from_id(session["user_id"])
    service_id = invitation.service
    user.add_to_service(
        service_id,
        invitation.permissions,
        invitation.folder_permissions,
        invitation.from_user.id,
    )
    return service_id
