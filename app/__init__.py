import os
import re

import dateutil
from flask import (Flask, session, Markup, escape, render_template, make_response)
from flask._compat import string_types
from flask_login import LoginManager
from flask_wtf import CsrfProtect
from werkzeug.exceptions import abort
from pygments import highlight
from pygments.lexers import JavascriptLexer
from pygments.formatters import HtmlFormatter
from app.notify_client.api_client import NotificationsAdminAPIClient
from app.notify_client.api_key_api_client import ApiKeyApiClient
from app.notify_client.user_api_client import UserApiClient
from app.notify_client.job_api_client import JobApiClient
from app.notify_client.notification_api_client import NotificationApiClient
from app.notify_client.status_api_client import StatusApiClient
from app.notify_client.permission_api_client import PermissionApiClient
from app.notify_client.invite_api_client import InviteApiClient
from app.its_dangerous_session import ItsdangerousSessionInterface
from app.asset_fingerprinter import AssetFingerprinter
from app.utils import validate_phone_number, InvalidPhoneError
import app.proxy_fix
from config import configs
from utils import logging

login_manager = LoginManager()
csrf = CsrfProtect()

notifications_api_client = NotificationsAdminAPIClient()
user_api_client = UserApiClient()
api_key_api_client = ApiKeyApiClient()
job_api_client = JobApiClient()
notification_api_client = NotificationApiClient()
status_api_client = StatusApiClient()
invite_api_client = InviteApiClient()
asset_fingerprinter = AssetFingerprinter()
permission_api_client = PermissionApiClient()


def create_app(config_name, config_overrides=None):
    application = Flask(__name__)

    application.config['NOTIFY_ADMIN_ENVIRONMENT'] = config_name
    application.config.from_object(configs[config_name])
    init_app(application, config_overrides)
    logging.init_app(application)
    init_csrf(application)

    notifications_api_client.init_app(application)
    user_api_client.init_app(application)
    api_key_api_client.init_app(application)
    job_api_client.init_app(application)
    notification_api_client.init_app(application)
    status_api_client.init_app(application)
    permission_api_client.init_app(application)
    invite_api_client.init_app(application)

    login_manager.init_app(application)
    login_manager.login_view = 'main.sign_in'
    login_manager.login_message_category = 'default'

    from app.main import main as main_blueprint
    application.register_blueprint(main_blueprint)

    from .status import status as status_blueprint
    application.register_blueprint(status_blueprint)

    proxy_fix.init_app(application)

    application.session_interface = ItsdangerousSessionInterface()

    application.add_template_filter(nl2br)
    application.add_template_filter(format_datetime)
    application.add_template_filter(syntax_highlight_json)
    application.add_template_filter(valid_phone_number)

    application.after_request(useful_headers_after_request)
    register_errorhandlers(application)

    return application


def init_csrf(application):
    csrf.init_app(application)

    @csrf.error_handler
    def csrf_handler(reason):
        if 'user_id' not in session:
            application.logger.info(
                u'csrf.session_expired: Redirecting user to log in page'
            )

            return application.login_manager.unauthorized()

        application.logger.info(
            u'csrf.invalid_token: Aborting request, user_id: {user_id}',
            extra={'user_id': session['user_id']})

        abort(400, reason)


def init_app(app, config_overrides):

    if config_overrides:
        for key in app.config.keys():
            if key in config_overrides:
                    app.config[key] = config_overrides[key]

    for key, value in app.config.items():
        if key in os.environ:
            app.config[key] = convert_to_boolean(os.environ[key])

    @app.context_processor
    def inject_global_template_variables():
        return {
            'asset_path': '/static/',
            'header_colour': app.config['HEADER_COLOUR'],
            'asset_url': asset_fingerprinter.get_url
        }


def convert_to_boolean(value):
    if isinstance(value, string_types):
        if value.lower() in ['t', 'true', 'on', 'yes', '1']:
            return True
        elif value.lower() in ['f', 'false', 'off', 'no', '0']:
            return False

    return value


def nl2br(value):
    _paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')

    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', Markup('<br>\n'))
                          for p in _paragraph_re.split(escape(value)))
    return Markup(result)


def syntax_highlight_json(code):
    return Markup(highlight(code, JavascriptLexer(), HtmlFormatter(noclasses=True)))


def format_datetime(date):
    date = dateutil.parser.parse(date)
    native = date.replace(tzinfo=None)
    return native.strftime('%A %d %B %Y at %H:%M')


def valid_phone_number(phone_number):
    try:
        validate_phone_number(phone_number)
        return True
    except InvalidPhoneError:
        return False


# https://www.owasp.org/index.php/List_of_useful_HTTP_headers
def useful_headers_after_request(response):
    response.headers.add('X-Frame-Options', 'deny')
    response.headers.add('X-Content-Type-Options', 'nosniff')
    response.headers.add('X-XSS-Protection', '1; mode=block')
    response.headers.add('Content-Security-Policy',
                         "default-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' data:;")  # noqa
    if 'Cache-Control' in response.headers:
        del response.headers['Cache-Control']
    response.headers.add(
        'Cache-Control', 'no-store, no-cache, private, must-revalidate')
    return response


def register_errorhandlers(application):
    def render_error(error):
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, 'code', 500)
        resp = make_response(render_template("error/{0}.html".format(error_code)), error_code)
        return useful_headers_after_request(resp)
    for errcode in [401, 404, 403, 500]:
        application.errorhandler(errcode)(render_error)


def get_app_version():
    build = 'n/a'
    build_time = "n/a"
    try:
        from app import version
        build = version.__build__
        build_time = version.__time__
    except:
        pass
    return build, build_time
