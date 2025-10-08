from flask import (
    Blueprint,
    abort,
    current_app,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from notifications_utils.recipients import RecipientCSV
from notifications_utils.template import HTMLEmailTemplate

from app import status_api_client
from app.formatters import format_thousands
from app.main import main
from app.main.forms import FieldWithNoneOption
from app.main.views_nl.sub_navigation_dictionaries import features_nav, using_notify_nav
from app.models.branding import EmailBranding
from app.models.letter_rates import LetterRates
from app.models.sms_rate import SMSRate
from app.utils.user import user_has_permissions

redirects = Blueprint("redirects", __name__)
main.register_blueprint(redirects)


@main.route("/")
def index():
    if current_user and current_user.is_authenticated:
        return redirect(url_for("main.your_services"))

    return render_template(
        "views/signedout.html",
        sms_rate=SMSRate(),
        counts=status_api_client.get_count_of_live_services_and_organisations(),
        letter_rates=LetterRates().rates,
    )


@main.route("/error/<int:status_code>")
def error(status_code):
    if status_code >= 500:
        abort(404)
    abort(status_code)


@main.route("/cookies")
def cookies():
    return render_template("views/cookies.html")


@main.route("/privacy")
def privacy():
    return render_template("views/privacy.html")


@main.route("/accessibility-statement")
def accessibility_statement():
    return render_template("views/accessibility_statement.html")


@main.route("/design-patterns-content-guidance")
def design_content():
    return redirect("https://www.gov.uk/service-manual/design/sending-emails-and-text-messages", 301)


@main.route("/_email")
def email_template():
    branding_style = request.args.get("branding_style")
    subject = request.args.get("title", default="Preview of email branding")
    email_branding_preview = request.args.get("email_branding_preview", False)

    if not branding_style or branding_style in {"govuk", FieldWithNoneOption.NONE_OPTION_VALUE}:
        branding = EmailBranding.govuk_branding()

    elif branding_style == "custom":
        branding = EmailBranding.with_default_values(**request.args)

    else:
        branding = EmailBranding.from_id(branding_style)

    template = {
        "template_type": "email",
        "subject": subject,
        "content": render_template(
            "example-email.md" if not email_branding_preview else "email-branding-preview-example-email.md"
        ),
    }

    resp = make_response(
        str(
            HTMLEmailTemplate(
                template,
                govuk_banner=branding.has_govuk_banner,
                brand_text=branding.text,
                brand_colour=branding.colour,
                brand_logo=branding.logo_url,
                brand_banner=branding.has_brand_banner,
                brand_alt_text=branding.alt_text,
                rebrand=True,
            )
        )
    )

    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    return resp


@main.route("/terms-of-use")
def terms_of_use():
    return render_template("views/terms-of-use.html")


@main.route("/new-terms-of-use")
def new_terms_of_use():
    # this route will be used occasionally - each time we change terms of use, so we keep the redirect here.
    return redirect(url_for("main.terms_of_use"))


# --- Guidance pages --- #


@main.route("/features")
def guidance_features():
    return render_template("views/guidance/features/index.html", navigation_links=features_nav())


@main.route("/features/roadmap")
def guidance_roadmap():
    return render_template("views/guidance/features/roadmap.html", navigation_links=features_nav())


@main.route("/features/security")
def guidance_security():
    return render_template("views/guidance/features/security.html", navigation_links=features_nav())


@main.route("/features/who-can-use-notify")
def guidance_who_can_use_notify():
    return render_template(
        "views/guidance/features/who-can-use-notify.html",
        navigation_links=features_nav(),
    )


@main.route("/using-notify")
def guidance_using_notify():
    return render_template(
        "views/guidance/using-notify/index.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/api-documentation")
def guidance_api_documentation():
    return render_template(
        "views/guidance/using-notify/api-documentation.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/attach-pages")
def guidance_attach_pages():
    return render_template(
        "views/guidance/using-notify/attach-pages.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/bulk-sending")
def guidance_bulk_sending():
    return render_template(
        "views/guidance/using-notify/bulk-sending.html",
        max_spreadsheet_rows=RecipientCSV.max_rows,
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/daily-limits")
def guidance_daily_limits():
    rate_limits = {
        type: format_thousands(limit) for type, limit in current_app.config["DEFAULT_LIVE_SERVICE_RATE_LIMITS"].items()
    }
    return render_template(
        "views/guidance/using-notify/daily-limits.html",
        max_spreadsheet_rows=RecipientCSV.max_rows,
        rate_limits=rate_limits,
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/message-status")
@main.route("/using-notify/message-status/<template_type:notification_type>")
def guidance_message_status(notification_type=None):
    if not notification_type:
        return redirect(url_for(".guidance_message_status", notification_type="email"))
    return render_template(
        "views/guidance/using-notify/message-status.html",
        navigation_links=using_notify_nav(),
        notification_type=notification_type,
    )


@main.route("/using-notify/data-retention-period")
def guidance_data_retention_period():
    return render_template(
        "views/guidance/using-notify/data-retention-period.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/delivery-times")
def guidance_delivery_times():
    return render_template(
        "views/guidance/using-notify/delivery-times.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/email-branding")
def guidance_email_branding():
    return render_template(
        "views/guidance/using-notify/email-branding.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/formatting")
def guidance_formatting():
    return render_template(
        "views/guidance/using-notify/formatting.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/letter-branding")
def guidance_letter_branding():
    return render_template(
        "views/guidance/using-notify/letter-branding.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/links-and-URLs")
def guidance_links_and_URLs():
    return render_template(
        "views/guidance/using-notify/links-and-URLs.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/optional-content")
def guidance_optional_content():
    return render_template(
        "views/guidance/using-notify/optional-content.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/personalisation")
def guidance_personalisation():
    return render_template(
        "views/guidance/using-notify/personalisation.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/qr-codes")
def guidance_qr_codes():
    return render_template(
        "views/guidance/using-notify/qr-codes.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/receive-text-messages")
def guidance_receive_text_messages():
    return render_template(
        "views/guidance/using-notify/receive-text-messages.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/reply-to-email-address")
def guidance_reply_to_email_address():
    return render_template(
        "views/guidance/using-notify/reply-to-email-address.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/schedule-messages")
def guidance_schedule_messages():
    return render_template(
        "views/guidance/using-notify/schedule-messages.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/send-files-by-email")
def guidance_send_files_by_email():
    return render_template(
        "views/guidance/using-notify/send-files-by-email.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/sign-in-method")
def guidance_sign_in_method():
    return render_template(
        "views/guidance/using-notify/sign-in-method.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/team-members-and-permissions")
def guidance_team_members_and_permissions():
    return render_template(
        "views/guidance/using-notify/team-members-permissions.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/templates")
def guidance_templates():
    return render_template(
        "views/guidance/using-notify/templates.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/text-message-sender")
def guidance_text_message_sender():
    return render_template(
        "views/guidance/using-notify/text-message-sender.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/trial-mode")
def guidance_trial_mode():
    return render_template(
        "views/guidance/using-notify/trial-mode.html",
        navigation_links=using_notify_nav(),
        email_and_sms_daily_limit=current_app.config["DEFAULT_SERVICE_LIMIT"],
    )


@main.route("/using-notify/upload-a-letter")
def guidance_upload_a_letter():
    return render_template(
        "views/guidance/using-notify/upload-a-letter.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/unsubscribe-links")
def guidance_unsubscribe_links():
    return render_template(
        "views/guidance/using-notify/unsubscribe-links.html",
        navigation_links=using_notify_nav(),
    )


# --- Redirects --- #


@main.route("/docs/notify-pdf-letter-spec-latest.pdf")
def letter_spec():
    return redirect("https://docs.notifications.service.gov.uk/documentation/images/notify-pdf-letter-spec-v2.4.pdf")


@main.route("/user-profile/mobile-number/delete", methods=["GET"])
def user_profile_mobile_number():
    return redirect(url_for("main.your_account_confirm_delete_mobile_number"), 301)


@main.route("/user-profile/mobile-number/delete", methods=["POST"])
def user_profile_mobile_number_delete():
    return redirect(url_for("main.your_account_mobile_number_delete"), 301)


@main.route("/user-profile/security-keys/<uuid:key_id>/delete", methods=["GET"])
def user_profile_confirm_delete_security_key(key_id):
    return redirect(url_for("main.your_account_confirm_delete_security_key"), 301)


@main.route("/user-profile/security-keys/<uuid:key_id>/delete", methods=["POST"])
def user_profile_delete_security_key(key_id):
    return redirect(url_for("main.your_account_delete_security_key"), 301)


@main.route("/services/<uuid:service_id>/service-settings/request-to-go-live", methods=["GET"])
@user_has_permissions("manage_service")
def request_to_go_live_old_path(service_id):
    return redirect(url_for("main.request_to_go_live", service_id=service_id), 301)


@main.route("/services/<uuid:service_id>/service-settings/request-to-go-live", methods=["POST"])
@user_has_permissions("manage_service")
def submit_request_to_go_live_old_path(service_id):
    return redirect(url_for("main.submit_request_to_go_live", service_id=service_id), 301)


def historical_redirects(new_endpoint, **kwargs):
    return redirect(url_for(new_endpoint, **kwargs), 301)


REDIRECTS = {
    "/accounts": "main.your_services",
    "/callbacks": "main.guidance_api_documentation",
    "/delivery-and-failure": "main.guidance_message_status",
    "/documentation": "main.guidance_api_documentation",
    "/features/email": "main.guidance_features",
    "/features/get-started": "main.guidance_features",
    "/features/letters": "main.guidance_features",
    "/features/messages-status": "main.guidance_message_status",
    "/features/sms": "main.guidance_features",
    "/features/terms": "main.terms_of_use",
    "/features/trial-mode": "main.guidance_trial_mode",
    "/features/using-notify": "main.guidance_using_notify",
    "/features/who-its-for": "main.guidance_who_can_use_notify",
    "/guidance_using_notify": "main.guidance_using_notify",
    "/information-risk-management": "main.guidance_security",
    "/information-security": "main.guidance_security",
    "/integration_testing": "main.guidance_api_documentation",
    "/integration-testing": "main.guidance_api_documentation",
    "/performance": "main.performance",
    "/pricing/trial-mode": "main.guidance_trial_mode",
    "/roadmap": "main.guidance_roadmap",
    "/terms": "main.terms_of_use",
    "/trial-mode": "main.guidance_trial_mode",
    "/using-notify/delivery-status": "main.guidance_message_status",
    "/using-notify/get-started": "main.guidance_features",
    "/using-notify/guidance": "main.guidance_using_notify",
    "/using-notify/guidance/branding-and-customisation": "main.guidance_using_notify",
    "/using-notify/guidance/bulk-sending": "main.guidance_bulk_sending",
    "/using-notify/guidance/delivery-times": "main.guidance_delivery_times",
    "/using-notify/guidance/edit-and-format-messages": "main.guidance_formatting",
    "/using-notify/guidance/email-branding": "main.guidance_email_branding",
    "/using-notify/guidance/letter-branding": "main.guidance_letter_branding",
    "/using-notify/guidance/letter-specification": "main.guidance_upload_a_letter",
    "/using-notify/guidance/message-status": "main.guidance_message_status",
    "/using-notify/guidance/message-status/<template_type:notification_type>": "main.guidance_message_status",
    "/using-notify/guidance/optional-content": "main.guidance_optional_content",
    "/using-notify/guidance/personalisation": "main.guidance_personalisation",
    "/using-notify/guidance/receive-text-messages": "main.guidance_receive_text_messages",
    "/using-notify/guidance/reply-to-email-address": "main.guidance_reply_to_email_address",
    "/using-notify/guidance/schedule-emails-and-text-messages": "main.guidance_schedule_messages",
    "/using-notify/guidance/schedule-messages": "main.guidance_schedule_messages",
    "/using-notify/guidance/send-files-by-email": "main.guidance_send_files_by_email",
    "/using-notify/guidance/team-members-and-permissions": "main.guidance_team_members_and_permissions",
    "/using-notify/guidance/templates": "main.guidance_templates",
    "/using-notify/guidance/text-message-sender": "main.guidance_text_message_sender",
    "/using-notify/guidance/upload-a-letter": "main.guidance_upload_a_letter",
    "/using-notify/trial-mode": "main.guidance_trial_mode",
    "/using-notify/who-can-use-notify": "main.guidance_who_can_use_notify",
    "/using-notify/who-its-for": "main.guidance_who_can_use_notify",
    "/user-profile": "main.your_account",
    "/user-profile/disable-platform-admin-view": "main.your_account_disable_platform_admin_view",
    "/user-profile/email": "main.your_account_email",
    "/user-profile/email/authenticate": "main.your_account_email_authenticate",
    "/user-profile/email/confirm/<string:token>": "main.your_account_email_confirm",
    "/user-profile/get-emails-about-new-features": "main.your_account_get_emails_about_new_features",
    "/user-profile/mobile-number": "main.your_account_mobile_number",
    "/user-profile/mobile-number/authenticate": "main.your_account_mobile_number_authenticate",
    "/user-profile/mobile-number/confirm": "main.your_account_mobile_number_confirm",
    "/user-profile/name": "main.your_account_name",
    "/user-profile/password": "main.your_account_password",
    "/user-profile/security-keys": "main.your_account_security_keys",
    "/user-profile/security-keys/<uuid:key_id>/manage": "main.your_account_manage_security_key",
    "/user-profile/take-part-in-user-research": "main.your_account_take_part_in_user_research",
}

for old_url, new_endpoint in REDIRECTS.items():
    redirects.add_url_rule(old_url, defaults={"new_endpoint": new_endpoint}, view_func=historical_redirects)
