from flask import (
    render_template,
    redirect,
    request,
    url_for,
    session,
    flash
)

from flask_login import (
    login_required,
    current_user
)
from notifications_python_client import HTTPError

from app import service_api_client
from app.main import main
from app.utils import user_has_permissions, email_safe
from app.main.forms import ConfirmPasswordForm, ServiceNameForm
from app import user_api_client
from app import current_service


@main.route("/services/<service_id>/service-settings")
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_settings(service_id):
    return render_template('views/service-settings.html')


@main.route("/services/<service_id>/service-settings/name", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_name_change(service_id):
    form = ServiceNameForm(service_api_client.find_all_service_email_from)

    if form.validate_on_submit():
        session['service_name_change'] = form.name.data
        return redirect(url_for('.service_name_change_confirm', service_id=service_id))

    return render_template(
        'views/service-settings/name.html',
        form=form)


@main.route("/services/<service_id>/service-settings/name/confirm", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_name_change_confirm(service_id):

    # Validate password for form
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)
    form = ConfirmPasswordForm(_check_password)

    if form.validate_on_submit():
        current_service['name'] = session['service_name_change']
        current_service['email_from'] = email_safe(session['service_name_change'])
        try:
            service_api_client.update_service(
                current_service['id'],
                current_service['name'],
                current_service['active'],
                current_service['message_limit'],
                current_service['restricted'],
                current_service['users'],
                current_service['email_from'])
        except HTTPError as e:
            error_msg = "Duplicate service name '{}'".format(session['service_name_change'])
            if e.status_code == 400 and error_msg in e.message['name']:
                # Redirect the user back to the change service name screen
                flash('This service name is already in use', 'error')
                return redirect(url_for('main.service_name_change', service_id=service_id))
            else:
                raise e
        else:
            session.pop('service_name_change')
            return redirect(url_for('.service_settings', service_id=service_id))
    return render_template(
        'views/service-settings/confirm.html',
        heading='Change your service name',
        form=form)


@main.route("/services/<service_id>/service-settings/request-to-go-live", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_request_to_go_live(service_id):
    if request.method == 'GET':
        return render_template(
            'views/service-settings/request-to-go-live.html'
        )
    elif request.method == 'POST':
        flash('Thanks your request to go live is being processed', 'default')
        # TODO implement whatever this action would do in the real world
        return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/switch-live")
@login_required
@user_has_permissions(admin_override=True)
def service_switch_live(service_id):
    service_api_client.update_service(
        current_service['id'],
        current_service['name'],
        current_service['active'],
        # TODO This limit should be set depending on the agreement signed by
        # with Notify.
        25000 if current_service['restricted'] else 50,
        False if current_service['restricted'] else True,
        current_service['users'],
        current_service['email_from'])
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/status", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_status_change(service_id):
    if request.method == 'GET':
        return render_template(
            'views/service-settings/status.html'
        )
    elif request.method == 'POST':
        return redirect(url_for('.service_status_change_confirm', service_id=service_id))


@main.route("/services/<service_id>/service-settings/status/confirm", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_status_change_confirm(service_id):
    # Validate password for form
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)
    form = ConfirmPasswordForm(_check_password)

    if form.validate_on_submit():
        current_service['active'] = True
        service_api_client.update_service(
            current_service['id'],
            current_service['name'],
            current_service['active'],
            current_service['message_limit'],
            current_service['restricted'],
            current_service['users'],
            current_service['email_from'])
        return redirect(url_for('.service_settings', service_id=service_id))
    return render_template(
        'views/service-settings/confirm.html',
        heading='Turn off all outgoing notifications',
        destructive=True,
        form=form)


@main.route("/services/<service_id>/service-settings/delete", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_delete(service_id):

    if request.method == 'GET':
        return render_template(
            'views/service-settings/delete.html'
        )
    elif request.method == 'POST':
        return redirect(url_for('.service_delete_confirm', service_id=service_id))


@main.route("/services/<service_id>/service-settings/delete/confirm", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_delete_confirm(service_id):

    # Validate password for form
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)
    form = ConfirmPasswordForm(_check_password)

    if form.validate_on_submit():
        service_api_client.delete_service(service_id)
        return redirect(url_for('.choose_service'))

    return render_template(
        'views/service-settings/confirm.html',
        heading='Delete this service from Notify',
        destructive=True,
        form=form)
