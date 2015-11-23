from flask import render_template

from app.main import main


@main.route('/index')
def index():
    return 'Hello from notifications-admin'


@main.route("/")
def idx():
    return render_template('index.html')


@main.route("/govuk")
def govuk():
    return render_template('govuk_template.html')


@main.route("/helloworld")
def helloworld():
    return render_template('hello-world.html')
