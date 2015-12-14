from flask import render_template, jsonify, redirect
from flask_login import login_required

from app.main import main
from app.main.forms import AddServiceForm


@main.route("/add-service", methods=['GET'])
@login_required
def add_service():
    return render_template('views/add-service.html', form=AddServiceForm())


@main.route("/add-service", methods=['POST'])
@login_required
def process_add_service():
    form = AddServiceForm()

    if form.validate_on_submit():

        return redirect('/dashboard')
    else:
        return jsonify(form.errors), 400
