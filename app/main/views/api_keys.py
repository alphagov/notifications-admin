from flask import request, render_template, redirect, url_for, flash, Markup, abort
from flask_login import login_required
from app.main import main
from app.main.forms import CreateKeyForm, Whitelist
from app import api_key_api_client, service_api_client, notification_api_client, current_service
from app.utils import user_has_permissions, email_safe
from app.notify_client.api_key_api_client import KEY_TYPE_NORMAL, KEY_TYPE_TEST, KEY_TYPE_TEAM


@main.route("/services/<service_id>/api")
@login_required
@user_has_permissions('manage_api_keys', admin_override=True)
def api_integration(service_id):
    return render_template(
        'views/api/index.html',
        api_notifications=notification_api_client.get_notifications_for_service(
            service_id=service_id,
            include_jobs=False,
            include_from_test_key=True
        )
    )


@main.route("/services/<service_id>/api/documentation")
@login_required
@user_has_permissions('manage_api_keys', admin_override=True)
def api_documentation(service_id):
    return render_template(
        'views/api/documentation.html'
    )


@main.route("/services/<service_id>/api/whitelist", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_api_keys', admin_override=True)
def whitelist(service_id):
    form = Whitelist()
    if form.validate_on_submit():
        service_api_client.update_whitelist(service_id, {
            'email_addresses': list(filter(None, form.email_addresses.data)),
            'phone_numbers':  list(filter(None, form.phone_numbers.data))
        })
        flash('Whitelist updated', 'default_with_tick')
        return redirect(url_for('.api_integration', service_id=service_id))
    if not form.errors:
        form.populate(**service_api_client.get_whitelist(service_id))
    return render_template(
        'views/api/whitelist.html',
        form=form
    )


@main.route("/services/<service_id>/api/keys")
@login_required
@user_has_permissions('manage_api_keys', admin_override=True)
def api_keys(service_id):
    return render_template(
        'views/api/keys.html',
        keys=api_key_api_client.get_api_keys(service_id=service_id)['apiKeys']
    )


@main.route("/services/<service_id>/api/keys/create", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_api_keys')
def create_api_key(service_id):
    key_names = [
        key['name'] for key in api_key_api_client.get_api_keys(service_id=service_id)['apiKeys']
    ]
    form = CreateKeyForm(key_names)
    form.key_type.choices = [
        (KEY_TYPE_NORMAL, 'Live – sends to anyone'),
        (KEY_TYPE_TEAM, 'Team and whitelist – limits who you can send to'),
        (KEY_TYPE_TEST, 'Test – pretends to send messages'),
    ]
    if current_service['restricted']:
        disabled_options = [KEY_TYPE_NORMAL]
        option_hints = {KEY_TYPE_NORMAL: Markup(
            'This option is not available because your service is in '
            '<a href="{}">trial mode</a>'.format(url_for(".trial_mode"))
        )}
    else:
        disabled_options, option_hints = [], {}
    if form.validate_on_submit():
        if form.key_type.data in disabled_options:
            abort(400)
        secret = api_key_api_client.create_api_key(
            service_id=service_id,
            key_name=form.key_name.data,
            key_type=form.key_type.data
        )
        return render_template(
            'views/api/keys/show.html',
            secret=secret,
            service_id=service_id,
            key_name=email_safe(form.key_name.data, whitespace='_')
        )
    return render_template(
        'views/api/keys/create.html',
        form=form,
        disabled_options=disabled_options,
        option_hints=option_hints
    )


@main.route("/services/<service_id>/api/keys/revoke/<key_id>", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_api_keys', admin_override=True)
def revoke_api_key(service_id, key_id):
    key_name = api_key_api_client.get_api_keys(service_id=service_id, key_id=key_id)['apiKeys'][0]['name']
    if request.method == 'GET':
        return render_template(
            'views/api/keys.html',
            revoke_key=key_name,
            keys=api_key_api_client.get_api_keys(service_id=service_id)['apiKeys'],
        )
    elif request.method == 'POST':
        api_key_api_client.revoke_api_key(service_id=service_id, key_id=key_id)
        flash('‘{}’ was revoked'.format(key_name), 'default_with_tick')
        return redirect(url_for('.api_keys', service_id=service_id))
