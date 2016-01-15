from flask import render_template, redirect, request, url_for, abort
from flask_login import login_required

from app.main import main
from app.main.forms import ConfirmPasswordForm, ServiceNameForm

service = {
    'name': 'Service name',
    'live': False,
    'active': True
}


@main.route("/services/<int:service_id>/service-settings")
@login_required
def service_settings(service_id):
    return render_template(
        'views/service-settings.html',
        service=service,
        service_id=service_id
    )


@main.route("/services/<int:service_id>/service-settings/name", methods=['GET', 'POST'])
@login_required
def name(service_id):

    form = ServiceNameForm()
    form.service_name.data = 'Service name'

    if request.method == 'GET':
        return render_template(
            'views/service-settings/name.html',
            service=service,
            form=form,
            service_id=service_id
        )
    elif request.method == 'POST':
        return redirect(url_for('.confirm_name_change', service_id=service_id))


@main.route("/services/<int:service_id>/service-settings/name/confirm", methods=['GET', 'POST'])
@login_required
def confirm_name_change(service_id):

    form = ConfirmPasswordForm()

    if request.method == 'GET':
        return render_template(
            'views/service-settings/confirm.html',
            heading='Change your service name',
            form=form,
            service_id=service_id
        )
    elif request.method == 'POST':
        return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<int:service_id>/service-settings/request-to-go-live", methods=['GET', 'POST'])
@login_required
def request_to_go_live(service_id):
    if request.method == 'GET':
        return render_template(
            'views/service-settings/request-to-go-live.html',
            service=service,
            service_id=service_id
        )
    elif request.method == 'POST':
        return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<int:service_id>/service-settings/status", methods=['GET', 'POST'])
@login_required
def status(service_id):
    if request.method == 'GET':
        return render_template(
            'views/service-settings/status.html',
            service=service,
            service_id=service_id
        )
    elif request.method == 'POST':
        return redirect(url_for('.confirm_status_change', service_id=service_id))


@main.route("/services/<int:service_id>/service-settings/status/confirm", methods=['GET', 'POST'])
@login_required
def confirm_status_change(service_id):

    form = ConfirmPasswordForm()

    if request.method == 'GET':
        return render_template(
            'views/service-settings/confirm.html',
            heading='Turn off all outgoing notifications',
            destructive=True,
            form=form,
            service_id=service_id
        )
    elif request.method == 'POST':
        return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<int:service_id>/service-settings/delete", methods=['GET', 'POST'])
@login_required
def delete(service_id):
    if request.method == 'GET':
        return render_template(
            'views/service-settings/delete.html',
            service=service,
            service_id=service_id
        )
    elif request.method == 'POST':
        return redirect(url_for('.confirm_delete', service_id=service_id))


@main.route("/services/<int:service_id>/service-settings/delete/confirm", methods=['GET', 'POST'])
@login_required
def confirm_delete(service_id):

    form = ConfirmPasswordForm()

    if request.method == 'GET':
        return render_template(
            'views/service-settings/confirm.html',
            heading='Delete this service from Notify',
            destructive=True,
            form=form,
            service_id=service_id
        )
    elif request.method == 'POST':
        return redirect(url_for('.service_dashboard', service_id=service_id))
