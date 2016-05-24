from flask import (
    render_template,
    redirect,
    session,
    url_for,
    request
)

from flask_login import login_user, current_user
from app.main import main
from app.main.forms import TwoFactorForm
from app import service_api_client
from app import user_api_client


@main.route('/two-factor', methods=['GET', 'POST'])
def two_factor():
    # TODO handle user_email not in session
    try:
        user_id = session['user_details']['id']
    except KeyError:
        return redirect('main.sign_in')

    def _check_code(code):
        return user_api_client.check_verify_code(user_id, code, "sms")

    form = TwoFactorForm(_check_code)

    if form.validate_on_submit():
        try:
            user = user_api_client.get_user(user_id)
            services = service_api_client.get_services({'user_id': str(user_id)}).get('data', [])
            # Check if coming from new password page
            if 'password' in session['user_details']:
                user.set_password(session['user_details']['password'])
                user.reset_failed_login_count()
                user_api_client.update_user(user)
            login_user(user, remember=True)
        finally:
            del session['user_details']

        next_url = request.args.get('next')
        if next_url and _is_safe_redirect_url(next_url):
            return redirect(next_url)

        if current_user.platform_admin:
            return redirect(url_for('main.show_all_services'))
        if len(services) == 1:
            return redirect(url_for('main.service_dashboard', service_id=services[0]['id']))
        else:
            return redirect(url_for('main.choose_service'))

    return render_template('views/two-factor.html', form=form)


# see http://flask.pocoo.org/snippets/62/
def _is_safe_redirect_url(target):
    from urllib.parse import urlparse, urljoin
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ('http', 'https') and \
        host_url.netloc == redirect_url.netloc
