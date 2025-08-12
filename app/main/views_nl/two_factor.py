from flask import (
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from itsdangerous import SignatureExpired
from notifications_utils.url_safe_token import check_token

from app import user_api_client
from app.main import main
from app.main.forms import TwoFactorForm
from app.models.token import Token
from app.models.user import User
from app.utils.login import (
    log_in_user,
    redirect_if_logged_in,
    redirect_to_sign_in,
)


@main.route("/two-factor-email-sent", methods=["GET"])
def two_factor_email_sent():
    title = "Email resent" if request.args.get("email_resent") else "Check your email"
    return render_template("views/two-factor-email.html", title=title, redirect_url=request.args.get("next"))


@main.route("/email-auth/<string:token>", methods=["GET"])
def two_factor_email_interstitial(token):
    return render_template("views/email-link-interstitial.html")


@main.route("/email-auth/<string:token>", methods=["POST"])
@redirect_if_logged_in
def two_factor_email(token):
    redirect_url = request.args.get("next")

    # checks url is valid, and hasn't timed out
    try:
        token_data = check_token(
            token,
            current_app.config["SECRET_KEY"],
            current_app.config["DANGEROUS_SALT"],
            current_app.config["EMAIL_2FA_EXPIRY_SECONDS"],
        )
    except SignatureExpired:
        return render_template("views/email-link-invalid.html", redirect_url=redirect_url)

    token = Token(token_data)

    # checks if code was already used
    logged_in, msg = user_api_client.check_verify_code(token.user_id, token.secret_code, "email")

    if not logged_in:
        return render_template("views/email-link-invalid.html", redirect_url=redirect_url)
    return log_in_user(token.user_id)


@main.route("/two-factor-sms", methods=["GET", "POST"])
@redirect_to_sign_in
def two_factor_sms():
    user_id = session["user_details"]["id"]
    user = User.from_id(user_id)

    def _check_code(code):
        return user_api_client.check_verify_code(user_id, code, "sms")

    form = TwoFactorForm(_check_code)
    redirect_url = request.args.get("next")

    if form.validate_on_submit():
        if user.email_needs_revalidating:
            user_api_client.send_verify_code(user.id, "email", None, redirect_url)
            return redirect(url_for(".revalidate_email_sent", next=redirect_url))
        else:
            return log_in_user(user_id)

    return render_template(
        "views/two-factor-sms.html",
        form=form,
        redirect_url=redirect_url,
        error_summary_enabled=True,
    )


@main.route("/two-factor-webauthn", methods=["GET"])
@redirect_to_sign_in
def two_factor_webauthn():
    user_id = session["user_details"]["id"]
    user = User.from_id(user_id)

    if not user.webauthn_auth:
        abort(403)

    return render_template("views/two-factor-webauthn.html")


@main.route("/re-validate-email", methods=["GET"])
def revalidate_email_sent():
    title = "Email resent" if request.args.get("email_resent") else "Check your email"
    redirect_url = request.args.get("next")
    return render_template("views/re-validate-email-sent.html", title=title, redirect_url=redirect_url)
