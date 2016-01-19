from flask import request, render_template, redirect, url_for, flash
from flask_login import login_required
from app.main import main
from app.main.forms import CreateKeyForm


@main.route("/services/<int:service_id>/documentation")
@login_required
def documentation(service_id):
    return render_template('views/documentation.html', service_id=service_id)


@main.route("/services/<int:service_id>/api-keys")
@login_required
def api_keys(service_id):
    return render_template(
        'views/api-keys.html',
        service_id=service_id,
        keys=[
            {'name': 'Test key 1', 'last_used': '12 January 2016, 10:01AM', 'id': 1},
            {'name': 'Test key 2', 'last_used': '12 January 2016, 9:50AM', 'id': 1},
            {'name': 'Test key 3', 'last_used': '12 January 2016, 9:49AM', 'id': 1},
            {
                'name': 'My first key', 'last_used': '25 December 2015, 09:49AM', 'id': 1,
                'revoked': '4 January 2016, 6:00PM'
            }
        ]
    )


@main.route("/services/<int:service_id>/api-keys/create", methods=['GET', 'POST'])
@login_required
def create_api_key(service_id):
    form = CreateKeyForm()
    if form.validate_on_submit():
        return redirect(url_for('.show_api_key', service_id=service_id))
    return render_template(
        'views/api-keys/create.html',
        service_id=service_id,
        key_name=form.key_name
    )


@main.route("/services/<int:service_id>/api-keys/show")
@login_required
def show_api_key(service_id):
    return render_template('views/api-keys/show.html', service_id=service_id)


@main.route("/services/<int:service_id>/api-keys/revoke/<int:key_id>", methods=['GET', 'POST'])
@login_required
def revoke_api_key(service_id, key_id):
    if request.method == 'GET':
        return render_template('views/api-keys/revoke.html', service_id=service_id)
    elif request.method == 'POST':
        flash('‘Test key 1’ was revoked')
        return redirect(url_for('.api_keys', service_id=service_id))
