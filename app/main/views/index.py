from flask import (
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
from notifications_utils.template import HTMLEmailTemplate, LetterImageTemplate

from app import letter_branding_client, status_api_client
from app.formatters import message_count
from app.main import main
from app.main.forms import FieldWithNoneOption
from app.main.views.pricing import CURRENT_SMS_RATE
from app.main.views.sub_navigation_dictionaries import features_nav, using_notify_nav
from app.models.branding import EmailBranding


@main.route("/")
def index():

    if current_user and current_user.is_authenticated:
        return redirect(url_for("main.choose_account"))

    return render_template(
        "views/signedout.html",
        sms_rate=CURRENT_SMS_RATE,
        counts=status_api_client.get_count_of_live_services_and_organisations(),
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


@main.route("/delivery-and-failure")
@main.route("/features/messages-status")
def delivery_and_failure():
    return redirect(url_for(".message_status"), 301)


@main.route("/design-patterns-content-guidance")
def design_content():
    return redirect("https://www.gov.uk/service-manual/design/sending-emails-and-text-messages", 301)


@main.route("/_email")
def email_template():
    branding_style = request.args.get("branding_style")

    if not branding_style or branding_style in {"govuk", FieldWithNoneOption.NONE_OPTION_VALUE}:
        branding = EmailBranding.govuk_branding()

    elif branding_style == "custom":
        branding = EmailBranding.with_default_values(**request.args)

    else:
        branding = EmailBranding.from_id(branding_style)

    template = {
        "template_type": "email",
        "subject": "Email branding preview",
        "content": render_template("example-email.md"),
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
            )
        )
    )

    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    return resp


@main.route("/_letter")
def letter_template():
    branding_style = request.args.get("branding_style")
    filename = request.args.get("filename")

    if branding_style == FieldWithNoneOption.NONE_OPTION_VALUE:
        branding_style = None
    if filename == FieldWithNoneOption.NONE_OPTION_VALUE:
        filename = None

    if branding_style:
        if filename:
            abort(400, "Cannot provide both branding_style and filename")
        filename = letter_branding_client.get_letter_branding(branding_style)["filename"]
    elif not filename:
        filename = "no-branding"

    template = {"subject": "", "content": "", "template_type": "letter"}
    image_url = url_for("no_cookie.letter_branding_preview_image", filename=filename)

    template_image = str(
        LetterImageTemplate(
            template,
            image_url=image_url,
            page_count=1,
        )
    )

    resp = make_response(render_template("views/service-settings/letter-preview.html", template=template_image))

    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    return resp


@main.route("/documentation")
def documentation():
    return render_template(
        "views/documentation.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/integration-testing")
def integration_testing():
    return render_template("views/integration-testing.html"), 410


@main.route("/callbacks")
def callbacks():
    return redirect(url_for("main.documentation"), 301)


# --- Features page set --- #


@main.route("/features")
def features():
    return render_template("views/features.html", navigation_links=features_nav())


@main.route("/features/roadmap", endpoint="roadmap")
def roadmap():
    return render_template("views/roadmap.html", navigation_links=features_nav())


@main.route("/features/security", endpoint="security")
def security():
    return render_template("views/security.html", navigation_links=features_nav())


@main.route("/terms-of-use", endpoint="terms_of_use")
def terms_of_use():
    return render_template("views/terms-of-use.html")


@main.route("/features/using-notify")
def using_notify():
    return render_template("views/using-notify.html", navigation_links=features_nav()), 410


@main.route("/features/get-started")
def get_started_old():
    return redirect(url_for(".get_started"), 301)


@main.route("/using-notify/get-started")
def get_started():
    return render_template(
        "views/get-started.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/features/who-its-for")
def who_its_for():
    return redirect(url_for(".who_can_use_notify"), 301)


@main.route("/features/who-can-use-notify")
def who_can_use_notify():
    return render_template(
        "views/guidance/who-can-use-notify.html",
        navigation_links=features_nav(),
    )


@main.route("/trial-mode")
@main.route("/features/trial-mode")
def trial_mode():
    return redirect(url_for(".trial_mode_new"), 301)


@main.route("/using-notify/trial-mode")
def trial_mode_new():
    return render_template(
        "views/trial-mode.html",
        navigation_links=using_notify_nav(),
        email_and_sms_daily_limit=current_app.config["DEFAULT_SERVICE_LIMIT"],
    )


@main.route("/using-notify/guidance")
def guidance_index():
    return render_template(
        "views/guidance/index.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/bulk-sending")
def guidance_bulk_sending():
    return render_template(
        "views/guidance/bulk-sending.html",
        max_spreadsheet_rows=RecipientCSV.max_rows,
        rate_limits=[
            message_count(limit, channel)
            for channel, limit in current_app.config["DEFAULT_LIVE_SERVICE_RATE_LIMITS"].items()
        ],
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/message-status")
@main.route("/using-notify/guidance/message-status/<template_type:notification_type>")
def message_status(notification_type=None):
    if not notification_type:
        return redirect(url_for(".message_status", notification_type="email"))
    return render_template(
        "views/guidance/message-status.html",
        navigation_links=using_notify_nav(),
        notification_type=notification_type,
    )


@main.route("/using-notify/guidance/delivery-times")
def guidance_delivery_times():
    return render_template(
        "views/guidance/delivery-times.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/email-branding")
def guidance_email_branding():
    return render_template(
        "views/guidance/email-branding.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/edit-and-format-messages")
def guidance_edit_and_format_messages():
    return render_template(
        "views/guidance/edit-and-format-messages.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/letter-branding")
def guidance_letter_branding():
    return render_template(
        "views/guidance/letter-branding.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/optional-content")
def guidance_optional_content():
    return render_template(
        "views/guidance/optional-content.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/personalisation")
def guidance_personalisation():
    return render_template(
        "views/guidance/personalisation.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/receive-text-messages")
def guidance_receive_text_messages():
    return render_template(
        "views/guidance/receive-text-messages.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/reply-to-email-address")
def guidance_reply_to_email_address():
    return render_template(
        "views/guidance/reply-to-email-address.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/schedule-messages")
def guidance_schedule_messages():
    return render_template(
        "views/guidance/schedule-messages.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/send-files-by-email")
def guidance_send_files_by_email():
    return render_template(
        "views/guidance/send-files-by-email.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/team-members-and-permissions")
def guidance_team_members_and_permissions():
    return render_template(
        "views/guidance/team-members-permissions.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/templates")
def guidance_templates():
    return render_template(
        "views/guidance/templates.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/text-message-sender")
def guidance_text_message_sender():
    return render_template(
        "views/guidance/text-message-sender.html",
        navigation_links=using_notify_nav(),
    )


@main.route("/using-notify/guidance/upload-a-letter")
def guidance_upload_a_letter():
    return render_template(
        "views/guidance/upload-a-letter.html",
        navigation_links=using_notify_nav(),
    )


# --- Redirects --- #


@main.route("/roadmap", endpoint="old_roadmap")
@main.route("/terms", endpoint="old_terms")
@main.route("/information-security", endpoint="information_security")
@main.route("/using_notify", endpoint="old_using_notify")
@main.route("/using-notify/guidance/schedule-emails-and-text-messages", endpoint="old_schedule_messages")
@main.route("/using-notify/guidance/branding-and-customisation", endpoint="old_branding_and_customisation")
@main.route("/information-risk-management", endpoint="information_risk_management")
@main.route("/integration_testing", endpoint="old_integration_testing")
@main.route("/features/sms", endpoint="old_features_sms")
@main.route("/features/email", endpoint="old_features_email")
@main.route("/features/letters", endpoint="old_features_letters")
@main.route("/features/terms", endpoint="old_features_terms")
@main.route("/using-notify/who-can-use-notify", endpoint="old_who_can_use_notify")
@main.route("/using-notify/who-its-for", endpoint="old_who_its_for")
@main.route("/using-notify/delivery-status", endpoint="old_delivery_status")
@main.route("/using-notify/guidance/letter-specification", endpoint="old_letter_specification")
def old_page_redirects():
    redirects = {
        "main.old_roadmap": "main.roadmap",
        "main.old_terms": "main.terms_of_use",
        "main.information_security": "main.using_notify",
        "main.old_using_notify": "main.using_notify",
        "main.information_risk_management": "main.security",
        "main.old_integration_testing": "main.integration_testing",
        "main.old_schedule_messages": "main.guidance_schedule_messages",
        "main.old_branding_and_customisation": "main.guidance_index",
        "main.old_features_sms": "main.features",
        "main.old_features_email": "main.features",
        "main.old_features_letters": "main.features",
        "main.old_features_terms": "main.terms_of_use",
        "main.old_who_can_use_notify": "main.who_can_use_notify",
        "main.old_who_its_for": "main.who_its_for",
        "main.old_delivery_status": "main.message_status",
        "main.old_letter_specification": "main.guidance_upload_a_letter",
    }
    return redirect(url_for(redirects[request.endpoint]), code=301)


@main.route("/docs/notify-pdf-letter-spec-latest.pdf")
def letter_spec():
    return redirect("https://docs.notifications.service.gov.uk" "/documentation/images/notify-pdf-letter-spec-v2.4.pdf")
