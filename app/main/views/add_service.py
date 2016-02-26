import re

from flask import render_template, request, redirect, session, url_for
from flask_login import login_required, current_user
from app.main import main
from app.main.dao import services_dao, users_dao
from app.main.forms import AddServiceForm


@main.route("/add-service", methods=['GET', 'POST'])
@login_required
def add_service():
    form = AddServiceForm(services_dao.find_all_service_names)
    heading = 'Which service do you want to set up notifications for?'
    if form.validate_on_submit():
        session['service_name'] = form.name.data
        user = users_dao.get_user_by_id(session['user_id'])
        service_id = services_dao.insert_new_service(session['service_name'], user.id)
        return redirect(url_for('main.service_dashboard', service_id=service_id))
    else:
        return render_template(
            'views/add-service.html',
            form=form,
            heading=heading
        )
