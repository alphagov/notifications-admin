from flask import request, render_template, redirect, url_for, flash, Markup, abort
from flask_login import login_required, current_user
from app.main import main
from app.main.forms import (
    CreateKeyForm,
    Whitelist,
    ServiceReceiveMessagesCallbackForm,
    ServiceDeliveryStatusCallbackForm
)
from app import api_key_api_client, service_api_client, notification_api_client, current_service
from app.utils import user_has_permissions, email_safe
from app.notify_client.api_key_api_client import KEY_TYPE_NORMAL, KEY_TYPE_TEST, KEY_TYPE_TEAM

dummy_bearer_token = 'bearer_token_set'


@main.route("/services/<service_id>/api")
@login_required
@user_has_permissions('manage_api_keys', admin_override=True)
def api_integration(service_id):
    callbacks_link = (
        '.api_callbacks' if 'inbound_sms' in current_service['permissions']
        else '.delivery_status_callback'
    )
    return render_template(
        'views/api/index.html',
        callbacks_link=callbacks_link,
        api_notifications=notification_api_client.get_api_notifications_for_service(service_id)
    )


@main.route("/services/<service_id>/api/documentation")
@login_required
@user_has_permissions('manage_api_keys', admin_override=True)
def api_documentation(service_id):
    return redirect(url_for('.documentation'), code=301)


@main.route("/services/<service_id>/api/whitelist", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_api_keys', admin_override=True)
def whitelist(service_id):
    form = Whitelist()
    if form.validate_on_submit():
        service_api_client.update_whitelist(service_id, {
            'email_addresses': list(filter(None, form.email_addresses.data)),
            'phone_numbers': list(filter(None, form.phone_numbers.data))
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
    disabled_options, option_hints = [], {}
    if current_service['restricted']:
        disabled_options = [KEY_TYPE_NORMAL]
        option_hints[KEY_TYPE_NORMAL] = Markup(
            'Not available because your service is in '
            '<a href="{}#trial-mode">trial mode</a>'.format(url_for(".using_notify"))
        )
    if 'letter' in current_service['permissions']:
        option_hints[KEY_TYPE_TEAM] = 'Can’t be used to send letters'
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


def get_apis():
    callback_api = None
    inbound_api = None
    if current_service['service_callback_api']:
        callback_api = service_api_client.get_service_callback_api(
            current_service['id'],
            current_service.get('service_callback_api')[0]
        )
    if current_service['inbound_api']:
        inbound_api = service_api_client.get_service_inbound_api(
            current_service['id'],
            current_service.get('inbound_api')[0]
        )

    return (callback_api, inbound_api)


def check_token_against_dummy_bearer(token):
    if token != dummy_bearer_token:
        return token
    else:
        return ''


@main.route("/services/<service_id>/api/callbacks", methods=['GET', 'POST'])
@login_required
def api_callbacks(service_id):
    if 'inbound_sms' not in current_service['permissions']:
        return redirect(url_for('.delivery_status_callback', service_id=service_id))

    received_text_messages_callback, delivery_status_callback = get_apis()

    return render_template(
        'views/api/callbacks.html',
        received_text_messages_callback=received_text_messages_callback.get('url', "Not Set"),
        delivery_status_callback=delivery_status_callback.get('url', "Not Set")
    )


def get_delivery_status_callback_details():
    if current_service['service_callback_api']:
        return service_api_client.get_service_callback_api(
            current_service['id'],
            current_service.get('service_callback_api')[0]
        )


@main.route("/services/<service_id>/api/callbacks/delivery-status-callback", methods=['GET', 'POST'])
@login_required
def delivery_status_callback(service_id):
    delivery_status_callback = get_delivery_status_callback_details()
    back_link = (
        '.api_callbacks' if 'inbound_sms' in current_service['permissions']
        else '.api_integration'
    )

    form = ServiceDeliveryStatusCallbackForm(
        url=delivery_status_callback.get('url') if delivery_status_callback else '',
        bearer_token=dummy_bearer_token if delivery_status_callback else ''
    )

    if form.validate_on_submit():
        if delivery_status_callback:
            if (delivery_status_callback.get('url') != form.url.data
                    or form.bearer_token.data != dummy_bearer_token):
                service_api_client.update_service_callback_api(
                    service_id,
                    url=form.url.data,
                    bearer_token=check_token_against_dummy_bearer(form.bearer_token.data),
                    user_id=current_user.id,
                    callback_api_id=delivery_status_callback.get('id')
                )
        else:
            service_api_client.create_service_callback_api(
                service_id,
                url=form.url.data,
                bearer_token=form.bearer_token.data,
                user_id=current_user.id
            )
        return redirect(url_for(back_link, service_id=service_id))

    return render_template(
        'views/api/callbacks/delivery-status-callback.html',
        back_link=back_link,
        form=form,
    )


def get_received_text_messages_callback():
    if current_service['inbound_api']:
        return service_api_client.get_service_inbound_api(
            current_service['id'],
            current_service.get('inbound_api')[0]
        )


@main.route("/services/<service_id>/api/callbacks/received-text-messages-callback", methods=['GET', 'POST'])
@login_required
def received_text_messages_callback(service_id):
    if 'inbound_sms' not in current_service['permissions']:
        return redirect(url_for('.api_integration', service_id=service_id))

    received_text_messages_callback = get_received_text_messages_callback()
    form = ServiceReceiveMessagesCallbackForm(
        url=received_text_messages_callback.get('url') if received_text_messages_callback else '',
        bearer_token=dummy_bearer_token if received_text_messages_callback else ''
    )

    if form.validate_on_submit():
        if received_text_messages_callback:
            if (received_text_messages_callback.get('url') != form.url.data
                    or form.bearer_token.data != dummy_bearer_token):
                service_api_client.update_service_inbound_api(
                    service_id,
                    url=form.url.data,
                    bearer_token=check_token_against_dummy_bearer(form.bearer_token.data),
                    user_id=current_user.id,
                    inbound_api_id=received_text_messages_callback.get('id')
                )
        else:
            service_api_client.create_service_inbound_api(
                service_id,
                url=form.url.data,
                bearer_token=form.bearer_token.data,
                user_id=current_user.id
            )
        return redirect(url_for('.api_callbacks', service_id=service_id))
    return render_template(
        'views/api/callbacks/received-text-messages-callback.html',
        form=form,
    )
