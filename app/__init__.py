import os

from flask import Flask
from flask._compat import string_types
from flask.ext import assets
from flask.ext.sqlalchemy import SQLAlchemy
from webassets.filter import get_filter

from config import configs

db = SQLAlchemy()


def create_app(config_name):
    application = Flask(__name__)

    application.config['NOTIFY_API_ENVIRONMENT'] = config_name
    application.config.from_object(configs[config_name])
    db.init_app(application)
    init_app(application)

    from app.main import main as main_blueprint
    application.register_blueprint(main_blueprint)

    return application


def init_app(app):
    for key, value in app.config.items():
        if key in os.environ:
            app.config[key] = convert_to_boolean(os.environ[key])

    init_asset_environment(app)


def init_asset_environment(app):
    env = assets.Environment(app)

    # Tell flask-assets where to look for our sass files.
    env.load_path = [
        os.path.join(os.path.dirname(__file__), 'assets/stylesheets'),
        os.path.join(os.path.dirname(__file__), 'assets'),
        os.path.join(os.path.dirname(__file__), 'assets/stylesheets/stylesheets/govuk_frontend_toolkit'),
        os.path.join(os.path.dirname(__file__), 'assets/stylesheets/govuk_template')

    ]

    scss = get_filter('scss', as_output=True)

    env.register(
        'css_all',
        assets.Bundle(
            'main.scss',
            filters='scss',
            output='css_all.css'
        )
    )

    env.register(
        'css_govuk-template',
        assets.Bundle(
            'govuk_template/govuk-template.scss',
            filters='scss',
            output='stylesheets/govuk-template.css'
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
