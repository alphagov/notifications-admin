import os
from flask import Flask, render_template
from flask.ext import assets
from flask.ext.script import Manager, Server
from webassets.filter import get_filter
from app import create_app


application = create_app()
manager = Manager(application)
port = int(os.environ.get('PORT', 6012))
manager.add_command("runserver", Server(host='0.0.0.0', port=port))

# debug mode - switch to False for production
application.config['ASSETS_DEBUG'] = True
application.config['DEBUG'] = True
env = assets.Environment(application)

# debug mode - switch to True for production
env.config['cache'] = False
env.config['manifest'] = False

# Tell flask-assets where to look for our sass files.
env.load_path = [
    os.path.join(os.path.dirname(__file__), 'app/assets/stylesheets'),
    os.path.join(os.path.dirname(__file__), 'app/assets'),
    os.path.join(os.path.dirname(__file__), 'app/assets/stylesheets/stylesheets/govuk_frontend_toolkit'),
    os.path.join(os.path.dirname(__file__), 'app/assets/stylesheets/govuk_template')

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


@manager.command
def list_routes():
    """List URLs of all application routes."""
    for rule in sorted(application.url_map.iter_rules(), key=lambda r: r.rule):
        print("{:10} {}".format(", ".join(rule.methods - set(['OPTIONS', 'HEAD'])), rule.rule))


if __name__ == '__main__':
    manager.run()
