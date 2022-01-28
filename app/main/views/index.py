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
from notifications_utils.template import HTMLEmailTemplate, LetterImageTemplate

from app import email_branding_client, letter_branding_client, status_api_client
from app.main import main
from app.main.forms import FieldWithNoneOption
from app.main.views.sub_navigation_dictionaries import (
    features_nav,
    using_notify_nav,
)
from app.utils import hide_from_search_engines


@main.route('/')
def index():

    if current_user and current_user.is_authenticated:
        return redirect(url_for('main.choose_account'))

    return render_template(
        'views/signedout.html',
        counts=status_api_client.get_count_of_live_services_and_organisations(),
    )


@main.route('/error/<int:status_code>')
def error(status_code):
    if status_code >= 500:
        abort(404)
    abort(status_code)


@main.route('/cookies')
def cookies():
    return render_template('views/cookies.html')


@main.route('/privacy')
def privacy():
    return render_template('views/privacy.html')


@main.route('/accessibility-statement')
def accessibility_statement():
    return render_template('views/accessibility_statement.html')


@main.route('/delivery-and-failure')
@main.route('/features/messages-status')
def delivery_and_failure():
    return redirect(url_for('.message_status'), 301)


@main.route('/design-patterns-content-guidance')
def design_content():
    return redirect('https://www.gov.uk/service-manual/design/sending-emails-and-text-messages', 301)


@main.route('/_email')
def email_template():
    branding_type = 'govuk'
    branding_style = request.args.get('branding_style', None)

    if branding_style == FieldWithNoneOption.NONE_OPTION_VALUE:
        branding_style = None

    if branding_style is not None:
        email_branding = email_branding_client.get_email_branding(branding_style)['email_branding']
        branding_type = email_branding['brand_type']

    if branding_type == 'govuk':
        brand_text = None
        brand_colour = None
        brand_logo = None
        govuk_banner = True
        brand_banner = False
        brand_name = None
    else:
        colour = email_branding['colour']
        brand_text = email_branding['text']
        brand_colour = colour
        brand_logo = (f"https://{current_app.config['LOGO_CDN_DOMAIN']}/{email_branding['logo']}"
                      if email_branding['logo'] else None)
        govuk_banner = branding_type in ['govuk', 'both']
        brand_banner = branding_type == 'org_banner'
        brand_name = email_branding['name']

    template = {
        'template_type': 'email',
        'subject': 'Email branding preview',
        'content': (
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
        )
    }

    if not bool(request.args):
        resp = make_response(str(HTMLEmailTemplate(template)))
    else:
        resp = make_response(str(HTMLEmailTemplate(
            template,
            govuk_banner=govuk_banner,
            brand_text=brand_text,
            brand_colour=brand_colour,
            brand_logo=brand_logo,
            brand_banner=brand_banner,
            brand_name=brand_name,
        )))

    resp.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return resp


@main.route('/_letter')
def letter_template():
    branding_style = request.args.get('branding_style')

    if branding_style == FieldWithNoneOption.NONE_OPTION_VALUE:
        branding_style = None

    if branding_style:
        filename = letter_branding_client.get_letter_branding(branding_style)['filename']
    else:
        filename = 'no-branding'

    template = {'subject': '', 'content': '', 'template_type': 'letter'}
    image_url = url_for('no_cookie.letter_branding_preview_image', filename=filename)

    template_image = str(LetterImageTemplate(
        template,
        image_url=image_url,
        page_count=1,
    ))

    resp = make_response(
        render_template('views/service-settings/letter-preview.html', template=template_image)
    )

    resp.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return resp


@main.route('/documentation')
def documentation():
    return render_template(
        'views/documentation.html',
        navigation_links=using_notify_nav(),
    )


@main.route('/integration-testing')
def integration_testing():
    return render_template('views/integration-testing.html'), 410


@main.route('/callbacks')
def callbacks():
    return redirect(url_for('main.documentation'), 301)


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


@main.route('/features/email')
@hide_from_search_engines
def features_email():
    return render_template(
        'views/features/emails.html',
        navigation_links=features_nav()
    )


@main.route('/features/sms')
def features_sms():
    return render_template(
        'views/features/text-messages.html',
        navigation_links=features_nav()
    )


@main.route('/features/letters')
def features_letters():
    return render_template(
        'views/features/letters.html',
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
        navigation_links=features_nav(),
    )


@main.route('/features/using-notify')
def using_notify():
    return render_template(
        'views/using-notify.html',
        navigation_links=features_nav()
    ), 410


@main.route('/using-notify/delivery-status')
def message_status():
    return render_template(
        'views/message-status.html',
        navigation_links=using_notify_nav(),
    )


@main.route('/features/get-started')
def get_started_old():
    return redirect(url_for('.get_started'), 301)


@main.route('/using-notify/get-started')
def get_started():
    return render_template(
        'views/get-started.html',
        navigation_links=using_notify_nav(),
    )


@main.route('/using-notify/who-its-for')
def who_its_for():
    return redirect(url_for('.who_can_use_notify'), 301)


@main.route('/using-notify/who-can-use-notify')
def who_can_use_notify():
    return render_template(
        'views/guidance/who-can-use-notify.html',
        navigation_links=features_nav(),
    )


@main.route('/trial-mode')
@main.route('/features/trial-mode')
def trial_mode():
    return redirect(url_for('.trial_mode_new'), 301)


@main.route('/using-notify/trial-mode')
def trial_mode_new():
    return render_template(
        'views/trial-mode.html',
        navigation_links=using_notify_nav(),
    )


@main.route('/using-notify/guidance')
def guidance_index():
    return render_template(
        'views/guidance/index.html',
        navigation_links=using_notify_nav(),
    )


@main.route('/using-notify/guidance/branding-and-customisation')
def branding_and_customisation():
    return render_template(
        'views/guidance/branding-and-customisation.html',
        navigation_links=using_notify_nav(),
    )


@main.route('/using-notify/guidance/create-and-send-messages')
def create_and_send_messages():
    return render_template(
        'views/guidance/create-and-send-messages.html',
        navigation_links=using_notify_nav(),
    )


@main.route('/using-notify/guidance/edit-and-format-messages')
def edit_and_format_messages():
    return render_template(
        'views/guidance/edit-and-format-messages.html',
        navigation_links=using_notify_nav(),
    )


@main.route('/using-notify/guidance/send-files-by-email')
def send_files_by_email():
    return render_template(
        'views/guidance/send-files-by-email.html',
        navigation_links=using_notify_nav(),
    )


@main.route('/using-notify/guidance/upload-a-letter')
def upload_a_letter():
    return render_template(
        'views/guidance/upload-a-letter.html',
        navigation_links=using_notify_nav(),
    )


@main.route('/using-notify/guidance/letter-specification')
def letter_specification():
    return render_template(
        'views/guidance/letter-specification.html',
        navigation_links=using_notify_nav(),
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


@main.route('/docs/notify-pdf-letter-spec-latest.pdf')
def letter_spec():
    return redirect(
        'https://docs.notifications.service.gov.uk'
        '/documentation/images/notify-pdf-letter-spec-v2.4.pdf'
    )
