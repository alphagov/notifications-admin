from flask import render_template, redirect, jsonify

from app.main import main
from app.main.forms import TwoFactorForm


@main.route("/two-factor", methods=['GET'])
def render_two_factor():
    return render_template('two-factor.html', form=TwoFactorForm())


@main.route('/two-factor', methods=['POST'])
def process_two_factor():
    form = TwoFactorForm()

    if form.validate_on_submit():
        return redirect('/dashboard')
    else:
        return jsonify(form.errors), 400
