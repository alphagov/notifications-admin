from flask import render_template, redirect, request, url_for, abort
from flask_login import login_required

from app.main import main

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
    if request.method == 'GET':
        return render_template(
            'views/service-settings/name.html',
            service=service
        )
    elif request.method == 'POST':
        return redirect(url_for('.confirm_name_change'))


@main.route("/service-settings/name/confirm", methods=['GET', 'POST'])
def confirm_name_change():
    if request.method == 'GET':
        return render_template(
            'views/service-settings/confirm.html',
            heading='Rename service',
            submit_button_text='Confirm'
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
    if request.method == 'GET':
        return render_template(
            'views/service-settings/confirm.html',
            heading='Turn off outgoing messages',
            submit_button_text='Confirm',
            destructive=True
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
    if request.method == 'GET':
        return render_template(
            'views/service-settings/confirm.html',
            heading='Delete service',
            submit_button_text='Confirm',
            destructive=True
        )
    elif request.method == 'POST':
        return redirect(url_for('.dashboard'))
