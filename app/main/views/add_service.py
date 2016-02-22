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
    services = services_dao.get_services(current_user.id)
    if len(services['data']) == 0:
        heading = 'Which service do you want to set up notifications for?'
    else:
        heading = 'Add a new service'
    if form.validate_on_submit():
        session['service_name'] = form.name.data
        return redirect(url_for('main.add_from_address'))
    else:
        return render_template(
            'views/add-service.html',
            form=form,
            heading=heading
        )


@main.route("/confirm-add-service", methods=['GET', 'POST'])
@login_required
def add_from_address():
    if request.method == 'POST':
        user = users_dao.get_user_by_id(session['user_id'])
        service_id = services_dao.insert_new_service(session['service_name'], user.id)
        return redirect(url_for('main.service_dashboard', service_id=service_id))
    else:
        return render_template(
            'views/add-from-address.html',
            service_name=session['service_name'],
            from_address="{}@notifications.service.gov.uk".format(_email_safe(session['service_name']))
        )


def _email_safe(string):
    return "".join([
        character.lower() if character.isalnum() or character == "." else ""
        for character in re.sub("\s+", ".", string.strip())
    ])
