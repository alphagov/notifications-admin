from flask import request, render_template, redirect, url_for, flash
from flask_login import login_required
from app.main import main
from app.main.forms import CreateKeyForm
from app import api_key_api_client
from app.utils import user_has_permissions


@main.route("/services/<service_id>/api-keys")
@login_required
@user_has_permissions('manage_api_keys')
def api_keys(service_id):
    return render_template(
        'views/api-keys.html',
        keys=api_key_api_client.get_api_keys(service_id=service_id)['apiKeys']
    )


@main.route("/services/<service_id>/api-keys/create", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_api_keys')
def create_api_key(service_id):
    key_names = [
        key['name'] for key in api_key_api_client.get_api_keys(service_id=service_id)['apiKeys']
    ]
    form = CreateKeyForm(key_names)
    if form.validate_on_submit():
        secret = api_key_api_client.create_api_key(service_id=service_id, key_name=form.key_name.data)
        return render_template('views/api-keys/show.html', secret=secret,
                               key_name=form.key_name.data)
    return render_template(
        'views/api-keys/create.html',
        form=form
    )


@main.route("/services/<service_id>/api-keys/revoke/<key_id>", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_api_keys')
def revoke_api_key(service_id, key_id):
    key_name = api_key_api_client.get_api_keys(service_id=service_id, key_id=key_id)['apiKeys'][0]['name']
    if request.method == 'GET':
        return render_template(
            'views/api-keys/revoke.html',
            key_name=key_name
        )
    elif request.method == 'POST':
        api_key_api_client.revoke_api_key(service_id=service_id, key_id=key_id)
        flash('‘{}’ was revoked'.format(key_name), 'default_with_tick')
        return redirect(url_for('.api_keys', service_id=service_id))
