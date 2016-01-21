from flask import request, render_template, redirect, url_for, flash
from flask_login import login_required
from app.main import main
from app.main.forms import CreateKeyForm
from app import api_key_api_client


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
        keys=api_key_api_client.get_api_keys(service_id=service_id)['apiKeys']
    )


@main.route("/services/<int:service_id>/api-keys/create", methods=['GET', 'POST'])
@login_required
def create_api_key(service_id):
    form = CreateKeyForm()
    if form.validate_on_submit():
        secret = api_key_api_client.create_api_key(service_id=service_id, key_name=form.key_name.data)
        return render_template('views/api-keys/show.html', service_id=service_id, secret=secret,
                               key_name=form.key_name.data)
    return render_template(
        'views/api-keys/create.html',
        service_id=service_id,
        key_name=form.key_name
    )


@main.route("/services/<int:service_id>/api-keys/revoke/<int:key_id>", methods=['GET', 'POST'])
@login_required
def revoke_api_key(service_id, key_id):
    key_name = api_key_api_client.get_api_keys(service_id=service_id, key_id=key_id)['apiKeys'][0]['name']
    if request.method == 'GET':
        return render_template(
            'views/api-keys/revoke.html',
            service_id=service_id,
            key_name=key_name
        )
    elif request.method == 'POST':
        api_key_api_client.revoke_api_key(service_id=service_id, key_id=key_id)
        flash('‘{}’ was revoked'.format(key_name))
        return redirect(url_for('.api_keys', service_id=service_id))
