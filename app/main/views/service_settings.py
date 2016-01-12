from flask import render_template, redirect, request, url_for, abort
from flask_login import login_required

from app.main import main
from app.main.forms import ConfirmPasswordForm, ServiceNameForm

service = {
    'name': 'Service name',
    'live': False,
    'active': True
}


@main.route("/service-settings")
def service_settings():
    return render_template(
        'views/service-settings.html',
        service=service
    )


@main.route("/service-settings/name", methods=['GET', 'POST'])
def name():

    form = ServiceNameForm()
    form.service_name.data = 'Service name'

    if request.method == 'GET':
        return render_template(
            'views/service-settings/name.html',
            service=service,
            form=form
        )
    elif request.method == 'POST':
        return redirect(url_for('.confirm_name_change'))


@main.route("/service-settings/name/confirm", methods=['GET', 'POST'])
def confirm_name_change():

    form = ConfirmPasswordForm()

    if request.method == 'GET':
        return render_template(
            'views/service-settings/confirm.html',
            heading='Change your service name',
            form=form
        )
    elif request.method == 'POST':
        return redirect(url_for('.service_settings'))


@main.route("/service-settings/request-to-go-live", methods=['GET', 'POST'])
def request_to_go_live():
    if request.method == 'GET':
        return render_template(
            'views/service-settings/request-to-go-live.html',
            service=service
        )
    elif request.method == 'POST':
        return redirect(url_for('.service_settings'))


@main.route("/service-settings/status", methods=['GET', 'POST'])
def status():
    if request.method == 'GET':
        return render_template(
            'views/service-settings/status.html',
            service=service
        )
    elif request.method == 'POST':
        return redirect(url_for('.confirm_status_change'))


@main.route("/service-settings/status/confirm", methods=['GET', 'POST'])
def confirm_status_change():

    form = ConfirmPasswordForm()

    if request.method == 'GET':
        return render_template(
            'views/service-settings/confirm.html',
            heading='Turn off all outgoing notifications',
            destructive=True,
            form=form
        )
    elif request.method == 'POST':
        return redirect(url_for('.service_settings'))


@main.route("/service-settings/delete", methods=['GET', 'POST'])
def delete():
    if request.method == 'GET':
        return render_template(
            'views/service-settings/delete.html',
            service=service
        )
    elif request.method == 'POST':
        return redirect(url_for('.confirm_delete'))


@main.route("/service-settings/delete/confirm", methods=['GET', 'POST'])
def confirm_delete():

    form = ConfirmPasswordForm()

    if request.method == 'GET':
        return render_template(
            'views/service-settings/confirm.html',
            heading='Delete this service from Notify',
            destructive=True,
            form=form
        )
    elif request.method == 'POST':
        return redirect(url_for('.dashboard'))
