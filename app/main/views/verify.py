from app.main import main
from flask import render_template, redirect, jsonify

from app.main.forms import VerifyForm


@main.route('/verify', methods=['GET'])
def render_verify():
    return render_template('verify.html', form=VerifyForm())


@main.route('/verify', methods=['POST'])
def process_verify():
    form = VerifyForm()

    if form.validate_on_submit():
        return redirect('/add-service')
    else:
        return jsonify(form.errors), 400
