from flask import current_app, render_template
from flask_login import current_user
from notifications_utils.international_billing_rates import (
    INTERNATIONAL_BILLING_RATES,
)

from app.main import main
from app.main.forms import SearchByNameForm
from app.main.views.sub_navigation_dictionaries import pricing_nav

CURRENT_SMS_RATE = '1.72'


@main.route('/pricing')
def pricing():
    return render_template(
        'views/pricing/index.html',
        sms_rate=CURRENT_SMS_RATE,
        international_sms_rates=sorted([
            (cc, country['names'], country['billable_units'])
            for cc, country in INTERNATIONAL_BILLING_RATES.items()
        ], key=lambda x: x[0]),
        search_form=SearchByNameForm(),
        navigation_links=pricing_nav(),
    )


@main.route('/pricing/how-to-pay')
def how_to_pay():
    return render_template(
        'views/pricing/how-to-pay.html',
        navigation_links=pricing_nav(),
    )


@main.route('/pricing/billing-details')
def billing_details():
    if current_user.is_authenticated:
        return render_template(
            'views/pricing/billing-details.html',
            billing_details=current_app.config['NOTIFY_BILLING_DETAILS'],
            navigation_links=pricing_nav(),
        )
    return render_template(
        'views/pricing/billing-details-signed-out.html',
        navigation_links=pricing_nav(),
    )
