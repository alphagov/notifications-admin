from flask import (
    render_template,
    redirect,
    session,
    url_for,
    current_app)

from flask_login import login_required

from app.main import main
from app.main.dao import services_dao
from app.main.forms import AddServiceForm
from app.notify_client.models import InvitedUser

from app import (
    invite_api_client,
    user_api_client,
    service_api_client
)


@main.route("/add-service", methods=['GET', 'POST'])
@login_required
def add_service():
    invited_user = session.get('invited_user')
    if invited_user:
        invitation = InvitedUser(**invited_user)
        # if invited user add to service and redirect to dashboard
        user = user_api_client.get_user(session['user_id'])
        service_id = invited_user['service']
        user_api_client.add_user_to_service(service_id, user.id, invitation.permissions)
        invite_api_client.accept_invite(service_id, invitation.id)
        return redirect(url_for('main.service_dashboard', service_id=service_id))

    form = AddServiceForm(services_dao.find_all_service_names)
    heading = 'Which service do you want to set up notifications for?'
    if form.validate_on_submit():
        session['service_name'] = form.name.data
        service_id = service_api_client.create_service(
            session['service_name'], False, current_app.config['DEFAULT_SERVICE_LIMIT'], True, session['user_id'])

        return redirect(url_for('main.service_dashboard', service_id=service_id))
    else:
        return render_template(
            'views/add-service.html',
            form=form,
            heading=heading
        )
