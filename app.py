import os
from flask import Flask, render_template
from flask.ext import assets
from webassets.filter import get_filter


app = Flask(__name__)

# debug mode - switch to False for production
app.config['ASSETS_DEBUG'] = True

env = assets.Environment(app)

# debug mode - switch to True for production
env.config['cache'] = False
env.config['manifest'] = False

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


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/govuk")
def govuk():
    return render_template('govuk_template.html')


@app.route("/helloworld")
def helloworld():
    return render_template('hello-world.html')


if __name__ == '__main__':
    app.run(debug=True)
