from flask import current_app, redirect, render_template, session, url_for
from flask_login import login_required
from notifications_python_client.errors import HTTPError

from app import billing_api_client, service_api_client
from app.main import main
from app.main.forms import CreateServiceForm
from app.utils import email_safe, user_is_gov_user


def _create_service(service_name, organisation_type, email_from, form):
    free_sms_fragment_limit = current_app.config['DEFAULT_FREE_SMS_FRAGMENT_LIMITS'].get(organisation_type)

    try:
        service_id = service_api_client.create_service(
            service_name=service_name,
            organisation_type=organisation_type,
            message_limit=current_app.config['DEFAULT_SERVICE_LIMIT'],
            restricted=True,
            user_id=session['user_id'],
            email_from=email_from,
        )
        session['service_id'] = service_id

        billing_api_client.create_or_update_free_sms_fragment_limit(service_id, free_sms_fragment_limit)

        return service_id, None
    except HTTPError as e:
        if e.status_code == 400 and e.message['name']:
            form.name.errors.append("This service name is already in use")
            return None, e
        else:
            raise e


def _create_example_template(service_id):
    example_sms_template = service_api_client.create_service_template(
        'Example text message template',
        'sms',
        'Hey ((name)), I’m trying out Notify. Today is ((day of week)) and my favourite colour is ((colour)).',
        service_id,
    )
    return example_sms_template


@main.route("/add-service", methods=['GET', 'POST'])
@login_required
@user_is_gov_user
def add_service():
    form = CreateServiceForm()
    heading = 'About your service'

    if form.validate_on_submit():
        email_from = email_safe(form.name.data)
        service_name = form.name.data

        service_id, error = _create_service(service_name, form.organisation_type.data, email_from, form)
        if error:
            return render_template('views/add-service.html', form=form, heading=heading)
        if len(service_api_client.get_active_services({'user_id': session['user_id']}).get('data', [])) > 1:
            return redirect(url_for('main.service_dashboard', service_id=service_id))

        example_sms_template = _create_example_template(service_id)

        return redirect(url_for(
            'main.start_tour',
            service_id=service_id,
            template_id=example_sms_template['data']['id'],
        ))
    else:
        return render_template(
            'views/add-service.html',
            form=form,
            heading=heading
        )
