import os
import re

from flask import Flask, session, Markup, render_template
from flask._compat import string_types
from flask.ext.sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CsrfProtect
from werkzeug.exceptions import abort

from app.notify_client.api_client import AdminAPIClient
from app.its_dangerous_session import ItsdangerousSessionInterface
import app.proxy_fix
from config import configs


db = SQLAlchemy()
login_manager = LoginManager()
csrf = CsrfProtect()

admin_api_client = AdminAPIClient()


def create_app(config_name):
    application = Flask(__name__)

    application.config['NOTIFY_API_ENVIRONMENT'] = config_name
    application.config.from_object(configs[config_name])
    if 'FLASK_CONFIG' in os.environ:
        application.config.from_envvar('FLASK_CONFIG')
    db.init_app(application)
    init_app(application)
    init_csrf(application)

    login_manager.init_app(application)
    login_manager.login_view = 'main.sign_in'

    from app.main import main as main_blueprint
    application.register_blueprint(main_blueprint)

    proxy_fix.init_app(application)

    application.session_interface = ItsdangerousSessionInterface()
    admin_api_client.init_app(application)

    application.add_template_filter(placeholders)
    application.add_template_filter(replace_placeholders)

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


def init_app(app):
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
    return response


def register_errorhandlers(application):
    def render_error(error):
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, 'code', 500)
        return render_template("error/{0}.html".format(error_code)), error_code
    for errcode in [401, 404, 500]:
        application.errorhandler(errcode)(render_error)
    return None
