from flask import current_app, render_template
from flask_login import current_user
from notifications_utils.international_billing_rates import INTERNATIONAL_BILLING_RATES

from app.main import main
from app.main.forms import SearchByNameForm
from app.main.views.sub_navigation_dictionaries import pricing_nav

CURRENT_SMS_RATE = "1.97"


@main.route("/pricing")
def guidance_pricing():
    return render_template(
        "views/guidance/pricing/index.html",
        navigation_links=pricing_nav(),
    )


@main.route("/pricing/text-messages")
def guidance_pricing_text_messages():
    return render_template(
        "views/guidance/pricing/text-message-pricing.html",
        sms_rate=CURRENT_SMS_RATE,
        international_sms_rates=sorted(
            [(cc, country["names"], country["billable_units"]) for cc, country in INTERNATIONAL_BILLING_RATES.items()],
            key=lambda x: x[0],
        ),
        _search_form=SearchByNameForm(),
        navigation_links=pricing_nav(),
    )


@main.route("/pricing/letters")
def guidance_pricing_letters():
    return render_template(
        "views/guidance/pricing/letter-pricing.html",
        navigation_links=pricing_nav(),
    )


@main.route("/pricing/trial-mode")
def guidance_trial_mode():
    return render_template(
        "views/guidance/pricing/trial-mode.html",
        navigation_links=pricing_nav(),
        email_and_sms_daily_limit=current_app.config["DEFAULT_SERVICE_LIMIT"],
    )


@main.route("/pricing/how-to-pay")
def guidance_how_to_pay():
    return render_template(
        "views/guidance/pricing/how-to-pay.html",
        navigation_links=pricing_nav(),
    )


@main.route("/pricing/billing-details")
def guidance_billing_details():
    if current_user.is_authenticated:
        return render_template(
            "views/guidance/pricing/billing-details.html",
            billing_details=current_app.config["NOTIFY_BILLING_DETAILS"],
            navigation_links=pricing_nav(),
        )
    return render_template(
        "views/guidance/pricing/billing-details-signed-out.html",
        navigation_links=pricing_nav(),
    )
