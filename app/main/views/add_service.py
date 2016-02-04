from flask import render_template, redirect, session, url_for
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
        user = users_dao.get_user_by_id(session['user_id'])
        service_id = services_dao.insert_new_service(form.name.data, user.id)
        session['service_name'] = form.name.data
        return redirect(url_for('main.service_dashboard', service_id=service_id))
    else:
        return render_template(
            'views/add-service.html',
            form=form,
            heading=heading
        )
