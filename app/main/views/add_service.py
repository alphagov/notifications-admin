from flask import render_template, jsonify, redirect, session
from flask_login import login_required
from app.main import main
from app.main.dao import services_dao, users_dao
from app.main.forms import AddServiceForm


@main.route("/add-service", methods=['GET', 'POST'])
@login_required
def add_service():
    form = AddServiceForm(services_dao.find_all_service_names())
    if form.validate_on_submit():

        user = users_dao.get_user_by_id(session['user_id'])
        services_dao.insert_new_service(form.service_name.data, user)
        return redirect('/dashboard')
    else:
        return render_template('views/add-service.html', form=form)
