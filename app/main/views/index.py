from flask import (render_template, url_for, redirect, request)
from app.main import main
from app import convert_to_boolean
from app.main.forms import SearchTemplatesForm
from flask_login import (login_required, current_user)

from notifications_utils.template import HTMLEmailTemplate
from notifications_utils.international_billing_rates import INTERNATIONAL_BILLING_RATES

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


@main.route('/integration_testing', endpoint='old_integration_testing')
@main.route('/integration-testing')
def integration_testing():
    if request.endpoint == "main.old_integration_testing":
        return redirect(url_for('.integration_testing'), code=301)
    else:
        return render_template('views/integration-testing.html')


@main.route('/callbacks')
def callbacks():
    return render_template('views/callbacks.html')


# --- Features --- #

@main.route('/features')
def features():
    return render_template(
        'views/features.html',
        navigation_links=features_nav()
    )


@main.route('/roadmap', endpoint='old_roadmap')
@main.route('/features/roadmap', endpoint='roadmap')
def roadmap():
    if request.endpoint == "main.old_roadmap":
        return redirect(url_for('.roadmap'), code=301)
    else:
        return render_template(
            'views/roadmap.html',
            navigation_links=features_nav()
        )


@main.route('/information-risk-management', endpoint='information_risk_management')
@main.route('/features/security', endpoint='security')
def security():
    if request.endpoint == "main.information_risk_management":
        return redirect(url_for('.security'), code=301)
    else:
        return render_template(
            'views/security.html',
            navigation_links=features_nav()
        )


@main.route('/terms', endpoint='old_terms')
@main.route('/features/terms', endpoint='terms')
def terms():
    if request.endpoint != "main.terms":
        return redirect(url_for('.terms'), code=301)
    else:
        return render_template(
            'views/terms-of-use.html',
            navigation_links=features_nav()
        )


@main.route('/information-security', endpoint='information_security')
@main.route('/using_notify', endpoint='old_using_notify')
@main.route('/features/using-notify')
def using_notify():
    if request.endpoint != "main.using_notify":
        return redirect(url_for('.using_notify'), code=301)
    else:
        return render_template(
            'views/using-notify.html',
            navigation_links=features_nav()
        )
