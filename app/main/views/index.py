from flask import redirect, render_template, request, url_for
from flask_login import current_user, login_required
from notifications_utils.international_billing_rates import (
    INTERNATIONAL_BILLING_RATES,
)
from notifications_utils.template import HTMLEmailTemplate

from app import convert_to_boolean
from app.main import main
from app.main.forms import SearchTemplatesForm
from app.main.views.sub_navigation_dictionaries import features_nav


@main.route('/')
def index():
    if current_user and current_user.is_authenticated:
        return redirect(url_for('main.choose_service'))
    return render_template('views/signedout.html')


@main.route("/verify-mobile")
@login_required
def verify_mobile():
    return render_template('views/verify-mobile.html')


@main.route('/cookies')
def cookies():
    return render_template('views/cookies.html')


@main.route('/trial-mode')
def trial_mode():
    return redirect(url_for('.using_notify') + '#trial-mode', 301)


@main.route('/pricing')
def pricing():
    return render_template(
        'views/pricing.html',
        sms_rate=0.0158,
        international_sms_rates=sorted([
            (cc, country['names'], country['billable_units'])
            for cc, country in INTERNATIONAL_BILLING_RATES.items()
        ], key=lambda x: x[0]),
        search_form=SearchTemplatesForm(),
    )


@main.route('/delivery-and-failure')
def delivery_and_failure():
    return redirect(url_for('.using_notify') + '#messagedeliveryandfailure', 301)


@main.route('/design-patterns-content-guidance')
def design_content():
    return render_template('views/design-patterns-content-guidance.html')


@main.route('/_email')
def email_template():
    return str(HTMLEmailTemplate({'subject': 'foo', 'content': (
        'Lorem Ipsum is simply dummy text of the printing and typesetting '
        'industry.\n\nLorem Ipsum has been the industry’s standard dummy '
        'text ever since the 1500s, when an unknown printer took a galley '
        'of type and scrambled it to make a type specimen book. '
        '\n\n'
        '# History'
        '\n\n'
        'It has '
        'survived not only'
        '\n\n'
        '* five centuries'
        '\n'
        '* but also the leap into electronic typesetting'
        '\n\n'
        'It was '
        'popularised in the 1960s with the release of Letraset sheets '
        'containing Lorem Ipsum passages, and more recently with desktop '
        'publishing software like Aldus PageMaker including versions of '
        'Lorem Ipsum.'
        '\n\n'
        '^ It is a long established fact that a reader will be distracted '
        'by the readable content of a page when looking at its layout.'
        '\n\n'
        'The point of using Lorem Ipsum is that it has a more-or-less '
        'normal distribution of letters, as opposed to using ‘Content '
        'here, content here’, making it look like readable English.'
        '\n\n\n'
        '1. One'
        '\n'
        '2. Two'
        '\n'
        '10. Three'
        '\n\n'
        'This is an example of an email sent using GOV.UK Notify.'
        '\n\n'
        'https://www.notifications.service.gov.uk'
    )}, govuk_banner=convert_to_boolean(request.args.get('govuk_banner', True))
    ))


@main.route('/documentation')
def documentation():
    return render_template('views/documentation.html')


@main.route('/integration-testing')
def integration_testing():
    return render_template('views/integration-testing.html')


@main.route('/callbacks')
def callbacks():
    return render_template('views/callbacks.html')


# --- Features page set --- #

@main.route('/features')
def features():
    return render_template(
        'views/features.html',
        navigation_links=features_nav()
    )


@main.route('/features/roadmap', endpoint='roadmap')
def roadmap():
    return render_template(
        'views/roadmap.html',
        navigation_links=features_nav()
    )


@main.route('/features/security', endpoint='security')
def security():
    return render_template(
        'views/security.html',
        navigation_links=features_nav()
    )


@main.route('/features/terms', endpoint='terms')
def terms():
    return render_template(
        'views/terms-of-use.html',
        navigation_links=features_nav()
    )


@main.route('/features/using-notify')
def using_notify():
    return render_template(
        'views/using-notify.html',
        navigation_links=features_nav()
    )


# --- Redirects --- #

@main.route('/roadmap', endpoint='old_roadmap')
@main.route('/terms', endpoint='old_terms')
@main.route('/information-security', endpoint='information_security')
@main.route('/using_notify', endpoint='old_using_notify')
@main.route('/information-risk-management', endpoint='information_risk_management')
@main.route('/integration_testing', endpoint='old_integration_testing')
def old_page_redirects():
    redirects = {
        'main.old_roadmap': 'main.roadmap',
        'main.old_terms': 'main.terms',
        'main.information_security': 'main.using_notify',
        'main.old_using_notify': 'main.using_notify',
        'main.information_risk_management': 'main.security',
        'main.old_integration_testing': 'main.integration_testing',
    }
    return redirect(url_for(redirects[request.endpoint]), code=301)
