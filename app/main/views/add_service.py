from flask import (
    render_template,
    redirect,
    session,
    url_for,
    current_app
)

from flask_login import (
    current_user,
    login_required
)

from werkzeug.exceptions import abort

from app.main import main
from app.main.forms import AddServiceForm
from app.notify_client.models import InvitedUser

from app import (
    invite_api_client,
    user_api_client,
    service_api_client
)

from app.utils import (
    email_safe,
    is_gov_user
)


def _add_invited_user_to_service(invited_user):
    invitation = InvitedUser(**invited_user)
    # if invited user add to service and redirect to dashboard
    user = user_api_client.get_user(session['user_id'])
    service_id = invited_user['service']
    user_api_client.add_user_to_service(service_id, user.id, invitation.permissions)
    invite_api_client.accept_invite(service_id, invitation.id)
    return service_id


def _create_service(service_name, email_from):
    service_id = service_api_client.create_service(service_name=service_name,
                                                   message_limit=current_app.config['DEFAULT_SERVICE_LIMIT'],
                                                   restricted=True,
                                                   user_id=session['user_id'],
                                                   email_from=email_from)
    session['service_id'] = service_id
    return service_id


@main.route("/add-service", methods=['GET', 'POST'])
@login_required
def add_service():
    invited_user = session.get('invited_user')
    if invited_user:
        service_id = _add_invited_user_to_service(invited_user)
        return redirect(url_for('main.service_dashboard', service_id=service_id))

    if not is_gov_user(current_user.email_address):
        abort(403)

    form = AddServiceForm(service_api_client.find_all_service_email_from)
    heading = 'Which service do you want to set up notifications for?'

    if form.validate_on_submit():
        email_from = email_safe(form.name.data)
        service_name = form.name.data
        service_id = _create_service(service_name, email_from)

        if (len(service_api_client.get_active_services({'user_id': session['user_id']}).get('data', [])) > 1):
            return redirect(url_for('main.service_dashboard', service_id=service_id))

        example_sms_template = service_api_client.create_service_template(
            'Example text message template',
            'sms',
            'Hey ((name)), I’m trying out Notify. Today is ((day of week)) and my favourite colour is ((colour)).',
            service_id
        )

        return redirect(url_for(
            'main.send_test',
            service_id=service_id,
            template_id=example_sms_template['data']['id'],
            help=1
        ))
    else:
        return render_template(
            'views/add-service.html',
            form=form,
            heading=heading
        )
