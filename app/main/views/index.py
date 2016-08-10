import markdown
import os
from flask import (render_template, url_for, redirect, Markup, request)
from app.main import main
from app import convert_to_boolean
from flask_login import login_required

from flask.ext.login import current_user
from mdx_gfm import GithubFlavoredMarkdownExtension

from notifications_utils.renderers import HTMLEmail


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
    return render_template('views/trial-mode.html')


@main.route('/pricing')
def pricing():
    return render_template('views/pricing.html')


@main.route('/delivery-and-failure')
def delivery_and_failure():
    return render_template('views/delivery-and-failure.html')


@main.route('/design-patterns-content-guidance')
def design_content():
    return render_template('views/design-patterns-content-guidance.html')


@main.route('/information-security')
def information_security():
    return render_template('views/information-security.html')


@main.route('/terms')
def terms():
    return render_template('views/terms-of-use.html')


@main.route('/_email')
def email_template():
    return HTMLEmail(
        govuk_banner=convert_to_boolean(request.args.get('govuk_banner', True))
    )(
        'Lorem Ipsum is simply dummy text of the printing and typesetting '
        'industry.\n\nLorem Ipsum has been the industry’s standard dummy '
        'text ever since the 1500s, when an unknown printer took a galley '
        'of type and scrambled it to make a type specimen book. '
        '\n\n'
        '# History'
        '\n\n'
        'It has '
        'survived not only'
        '\n'
        '*five centuries'
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
        'This is an example of an email sent using GOV.UK Notify.'
    )


@main.route('/documentation')
def documentation():
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(curr_dir, '../../../docs/index.md'), encoding='utf-8') as source:
        return render_template(
            'views/documentation.html',
            body=Markup(markdown.markdown(
                source.read(),
                extensions=[GithubFlavoredMarkdownExtension()]
            ))
        )
