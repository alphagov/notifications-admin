import os
import re

from flask import Flask, session, Markup
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
    login_manager.login_view = 'main.render_sign_in'

    from app.main import main as main_blueprint
    application.register_blueprint(main_blueprint)

    proxy_fix.init_app(application)

    application.session_interface = ItsdangerousSessionInterface()
    admin_api_client.init_app(application)

    application.add_template_filter(placeholders)
    application.add_template_filter(replace_placeholders)

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

    init_asset_environment(app)

    @app.context_processor
    def inject_global_template_variables():
        return {'asset_path': '/static/'}


def init_asset_environment(app):
    env = assets.Environment(app)

    # Tell flask-assets where to look for our sass files.
    env.load_path = [
        os.path.join(os.path.dirname(__file__), 'assets'),
        os.path.join(os.path.dirname(__file__), 'assets/stylesheets'),
        os.path.join(os.path.dirname(__file__), 'assets/stylesheets/stylesheets/govuk_frontend_toolkit'),
        os.path.join(os.path.dirname(__file__), 'assets/stylesheets/govuk_template'),
        os.path.join(os.path.dirname(__file__), 'assets/stylesheets/views'),
        os.path.join(os.path.dirname(__file__), 'assets/stylesheets/components'),
    ]

    scss = get_filter('scss', as_output=True)

    env.register(
        'css_all',
        assets.Bundle(
            'main.scss',
            filters='scss',
            output='stylesheets/css_all.css'
        )
    )

    env.register(
        'css_govuk-template',
        assets.Bundle(
            'govuk_template/govuk-template.scss',
            filters='scss',
            output='stylesheets/govuk-template.css',
            depends='*.scss'
        )
    )

    env.register(
        'css_govuk-template-ie6',
        assets.Bundle(
            'govuk_template/govuk-template-ie6.scss',
            filters='scss',
            output='stylesheets/govuk-template-ie6.css'
        )
    )

    env.register(
        'css_govuk-template-ie7',
        assets.Bundle(
            'govuk_template/govuk-template-ie7.scss',
            filters='scss',
            output='stylesheets/govuk-template-ie7.css'
        )
    )

    env.register(
        'css_govuk-template-ie8',
        assets.Bundle(
            'govuk_template/govuk-template-ie8.scss',
            filters='scss',
            output='stylesheets/govuk-template-ie8.css'
        )
    )

    env.register(
        'css_govuk-template-print',
        assets.Bundle(
            'govuk_template/govuk-template-print.scss',
            filters='scss',
            output='stylesheets/govuk-template-print.css'
        )
    )


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
