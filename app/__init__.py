import os
import re

from flask import Flask, session, Markup, escape, render_template
from flask._compat import string_types
from flask.ext.sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CsrfProtect
from werkzeug.exceptions import abort
from app.notify_client.api_client import NotificationsAdminAPIClient
from app.its_dangerous_session import ItsdangerousSessionInterface
import app.proxy_fix
from config import configs
from utils import logging

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CsrfProtect()

notifications_api_client = NotificationsAdminAPIClient()


def create_app(config_name, config_overrides=None):
    application = Flask(__name__)

    application.config['NOTIFY_ADMIN_ENVIRONMENT'] = config_name
    application.config.from_object(configs[config_name])
    init_app(application, config_overrides)
    db.init_app(application)
    init_csrf(application)
    logging.init_app(application)

    notifications_api_client.init_app(application)

    login_manager.init_app(application)
    login_manager.login_view = 'main.sign_in'

    from app.main import main as main_blueprint
    application.register_blueprint(main_blueprint)

    from .status import status as status_blueprint
    application.register_blueprint(status_blueprint)

    proxy_fix.init_app(application)

    application.session_interface = ItsdangerousSessionInterface()

    application.add_template_filter(placeholders)
    application.add_template_filter(replace_placeholders)
    application.add_template_filter(nl2br)

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
        return {'asset_path': '/static/'}


def convert_to_boolean(value):
    if isinstance(value, string_types):
        if value.lower() in ['t', 'true', 'on', 'yes', '1']:
            return True
        elif value.lower() in ['f', 'false', 'off', 'no', '0']:
            return False

    return value


def placeholders(value):
    if not value:
        return value
    return Markup(re.sub(
        r"\(\(([^\)]+)\)\)",  # anything that looks like ((registration number))
        lambda match: "<span class='placeholder'>{}</span>".format(match.group(1)),
        value
    ))


def nl2br(value):
    _paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')

    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', Markup('<br>\n'))
                          for p in _paragraph_re.split(escape(value)))
    return Markup(result)


def replace_placeholders(template, values):
    if not template:
        return template
    return Markup(re.sub(
        r"\(\(([^\)]+)\)\)",  # anything that looks like ((registration number))
        lambda match: values.get(match.group(1), ''),
        template
    ))


# https://www.owasp.org/index.php/List_of_useful_HTTP_headers
def useful_headers_after_request(response):
    response.headers.add('X-Frame-Options', 'deny')
    response.headers.add('X-Content-Type-Options', 'nosniff')
    response.headers.add('X-XSS-Protection', '1; mode=block')
    response.headers.add('Content-Security-Policy',
                         "default-src 'self' 'unsafe-inline'; font-src 'self' data:;")  # noqa
    return response


def register_errorhandlers(application):
    def render_error(error):
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, 'code', 500)
        return render_template("error/{0}.html".format(error_code)), error_code
    for errcode in [401, 404, 500]:
        application.errorhandler(errcode)(render_error)
