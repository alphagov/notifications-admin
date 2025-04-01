from datetime import UTC, datetime

from flask import current_app, render_template
from flask_login import current_user
from notifications_utils.international_billing_rates import INTERNATIONAL_BILLING_RATES

from app.main import main
from app.main.forms import SearchByNameForm
from app.main.views.sub_navigation_dictionaries import pricing_nav
from app.models.letter_rates import LetterRates
from app.models.sms_rate import SMSRate


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
        sms_rate=SMSRate(),
        international_sms_rates=sorted(
            [(cc, country["names"], country["rate_multiplier"]) for cc, country in INTERNATIONAL_BILLING_RATES.items()],
            key=lambda x: x[0],
        ),
        _search_form=SearchByNameForm(),
        navigation_links=pricing_nav(),
        last_updated=datetime(2025, 4, 1).astimezone(UTC),
    )


@main.route("/pricing/letters")
def guidance_pricing_letters():
    return render_template(
        "views/guidance/pricing/letter-pricing.html",
        navigation_links=pricing_nav(),
        letter_rates=LetterRates(),
    )


@main.route("/pricing/how-to-pay")
def guidance_how_to_pay():
    return render_template(
        "views/guidance/pricing/how-to-pay.html",
        billing_details=current_app.config["BILLING_DETAILS"],
        navigation_links=pricing_nav(),
    )


@main.route("/pricing/billing-details")
def guidance_billing_details():
    if current_user.is_authenticated:
        return render_template(
            "views/guidance/pricing/billing-details.html",
            billing_details=current_app.config["BILLING_DETAILS"],
            navigation_links=pricing_nav(),
        )
    return render_template(
        "views/guidance/pricing/billing-details-signed-out.html",
        navigation_links=pricing_nav(),
    )
