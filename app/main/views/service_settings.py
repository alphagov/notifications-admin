from flask import render_template, redirect, request, url_for, abort
from flask_login import login_required

from app.main import main
from app.main.dao.services_dao import (get_service_by_id, delete_service)
from app.main.forms import ConfirmPasswordForm, ServiceNameForm
from client.errors import HTTPError


@main.route("/services/<int:service_id>/service-settings")
@login_required
def service_settings(service_id):
    try:
        service = get_service_by_id(service_id)['data']
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e
    return render_template(
        'views/service-settings.html',
        service=service,
        service_id=service_id
    )


@main.route("/services/<int:service_id>/service-settings/name", methods=['GET', 'POST'])
@login_required
def service_name_change(service_id):
    try:
        service = get_service_by_id(service_id)
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e

    form = ServiceNameForm()

    if form.validate_on_submit():
        return redirect(url_for('.service_name_change_confirm', service_id=service_id))

    return render_template(
            'views/service-settings/name.html',
            service=service,
            form=form,
            service_id=service_id)


@main.route("/services/<int:service_id>/service-settings/name/confirm", methods=['GET', 'POST'])
@login_required
def service_name_change_confirm(service_id):
    try:
        service = get_service_by_id(service_id)
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e

    form = ConfirmPasswordForm()

    if form.validate_on_submit():
        # TODO send call to API
        return redirect(url_for('.service_settings', service_id=service_id))
    return render_template(
            'views/service-settings/confirm.html',
            heading='Change your service name',
            form=form,
            service_id=service_id)        


@main.route("/services/<int:service_id>/service-settings/request-to-go-live", methods=['GET', 'POST'])
@login_required
def service_request_to_go_live(service_id):
    try:
        service = get_service_by_id(service_id)
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e
    if request.method == 'GET':
        return render_template(
            'views/service-settings/request-to-go-live.html',
            service=service,
            service_id=service_id
        )
    elif request.method == 'POST':
        # TODO send call to API
        return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<int:service_id>/service-settings/status", methods=['GET', 'POST'])
@login_required
def service_status_change(service_id):
    try:
        service = get_service_by_id(service_id)
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e

    if request.method == 'GET':
        return render_template(
            'views/service-settings/status.html',
            service=service,
            service_id=service_id
        )
    elif request.method == 'POST':
        # TODO send call to API
        return redirect(url_for('.service_status_change_confirm', service_id=service_id))


@main.route("/services/<int:service_id>/service-settings/status/confirm", methods=['GET', 'POST'])
@login_required
def service_status_change_confirm(service_id):
    try:
        service = get_service_by_id(service_id)
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e

    # TODO validate password, will leave until
    # user management has been moved to the api.
    form = ConfirmPasswordForm()

    if form.validate_on_submit():
        return redirect(url_for('.service_settings', service_id=service_id))
    return render_template(
            'views/service-settings/confirm.html',
            heading='Turn off all outgoing notifications',
            destructive=True,
            form=form,
            service_id=service_id)


@main.route("/services/<int:service_id>/service-settings/delete", methods=['GET', 'POST'])
@login_required
def service_delete(service_id):
    try:
        service = get_service_by_id(service_id)
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e

    if request.method == 'GET':
        return render_template(
            'views/service-settings/delete.html',
            service=service,
            service_id=service_id
        )
    elif request.method == 'POST':
        return redirect(url_for('.service_delete_confirm', service_id=service_id))


@main.route("/services/<int:service_id>/service-settings/delete/confirm", methods=['GET', 'POST'])
@login_required
def service_delete_confirm(service_id):
    try:
        service = get_service_by_id(service_id)
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e
    # TODO validate password, will leave until
    # user management has been moved to the api.
    form = ConfirmPasswordForm()

    if form.validate_on_submit():
        try:
            service = delete_service(service_id)
        except HTTPError as e:
            if e.status_code == 404:
                abort(404)
            else:
                raise e
        return redirect(url_for('.choose_service'))

    return render_template(
        'views/service-settings/confirm.html',
        heading='Delete this service from Notify',
        destructive=True,
        form=form,
        service_id=service_id)
