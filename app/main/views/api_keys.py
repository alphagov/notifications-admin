from flask import (
    Markup,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

from app import (
    api_key_api_client,
    current_service,
    notification_api_client,
    service_api_client,
)
from app.formatters import email_safe
from app.main import main
from app.main.forms import CallbackForm, CreateKeyForm, GuestList
from app.notify_client.api_key_api_client import (
    KEY_TYPE_NORMAL,
    KEY_TYPE_TEAM,
    KEY_TYPE_TEST,
)
from app.utils.user import user_has_permissions

dummy_bearer_token = 'bearer_token_set'


@main.route("/services/<uuid:service_id>/api")
@user_has_permissions('manage_api_keys')
def api_integration(service_id):
    callbacks_link = (
        '.api_callbacks' if current_service.has_permission('inbound_sms')
        else '.delivery_status_callback'
    )
    return render_template(
        'views/api/index.html',
        callbacks_link=callbacks_link,
        api_notifications=notification_api_client.get_api_notifications_for_service(service_id)
    )


@main.route("/services/<uuid:service_id>/api/documentation")
@user_has_permissions('manage_api_keys')
def api_documentation(service_id):
    return redirect(url_for('.documentation'), code=301)


@main.route("/services/<uuid:service_id>/api/whitelist", methods=['GET', 'POST'], endpoint='old_guest_list')
@main.route("/services/<uuid:service_id>/api/guest-list", methods=['GET', 'POST'])
@user_has_permissions('manage_api_keys')
def guest_list(service_id):
    form = GuestList()
    if form.validate_on_submit():
        service_api_client.update_guest_list(service_id, {
            'email_addresses': list(filter(None, form.email_addresses.data)),
            'phone_numbers': list(filter(None, form.phone_numbers.data))
        })
        flash('Guest list updated', 'default_with_tick')
        return redirect(url_for('.api_integration', service_id=service_id))
    if not form.errors:
        form.populate(**service_api_client.get_guest_list(service_id))
    return render_template(
        'views/api/guest-list.html',
        form=form
    )


@main.route("/services/<uuid:service_id>/api/keys")
@user_has_permissions('manage_api_keys')
def api_keys(service_id):
    return render_template(
        'views/api/keys.html',
    )


@main.route("/services/<uuid:service_id>/api/keys/create", methods=['GET', 'POST'])
@user_has_permissions('manage_api_keys', restrict_admin_usage=True)
def create_api_key(service_id):
    form = CreateKeyForm(current_service.api_keys)
    form.key_type.choices = [
        (KEY_TYPE_NORMAL, 'Live – sends to anyone'),
        (KEY_TYPE_TEAM, 'Team and guest list – limits who you can send to'),
        (KEY_TYPE_TEST, 'Test – pretends to send messages'),
    ]
    # preserve order of items extended by starting with empty dicts
    form.key_type.param_extensions = {'items': [{}, {}]}
    if current_service.trial_mode:
        form.key_type.param_extensions['items'][0] = {
            'disabled': True,
            'hint': {
                'html': Markup(
                    'Not available because your service is in '
                    '<a class="govuk-link govuk-link--no-visited-state" href="/features/trial-mode">trial mode</a>')
            }
        }
    if current_service.has_permission('letter'):
        form.key_type.param_extensions['items'][1]['hint'] = {'text': 'Cannot be used to send letters'}
    if form.validate_on_submit():
        if current_service.trial_mode and form.key_type.data == KEY_TYPE_NORMAL:
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
        form=form
    )


@main.route("/services/<uuid:service_id>/api/keys/revoke/<uuid:key_id>", methods=['GET', 'POST'])
@user_has_permissions('manage_api_keys')
def revoke_api_key(service_id, key_id):
    key_name = current_service.get_api_key(key_id)['name']
    if request.method == 'GET':
        flash([
            "Are you sure you want to revoke ‘{}’?".format(key_name),
            "You will not be able to use this API key to connect to GOV.UK Notify."
        ], 'revoke this API key')
        return render_template(
            'views/api/keys.html',
        )
    elif request.method == 'POST':
        api_key_api_client.revoke_api_key(service_id=service_id, key_id=key_id)
        flash('‘{}’ was revoked'.format(key_name), 'default_with_tick')
        return redirect(url_for('.api_keys', service_id=service_id))


def get_apis():
    callback_api = None
    inbound_api = None
    if current_service.service_callback_api:
        callback_api = service_api_client.get_service_callback_api(
            current_service.id,
            current_service.service_callback_api[0]
        )
    if current_service.inbound_api:
        inbound_api = service_api_client.get_service_inbound_api(
            current_service.id,
            current_service.inbound_api[0]
        )

    return (callback_api, inbound_api)


def check_token_against_dummy_bearer(token):
    if token != dummy_bearer_token:
        return token
    else:
        return ''


@main.route("/services/<uuid:service_id>/api/callbacks", methods=['GET'])
@user_has_permissions('manage_api_keys')
def api_callbacks(service_id):
    if not current_service.has_permission('inbound_sms'):
        return redirect(url_for('.delivery_status_callback', service_id=service_id))

    delivery_status_callback, received_text_messages_callback = get_apis()

    return render_template(
        'views/api/callbacks.html',
        received_text_messages_callback=received_text_messages_callback['url']
        if received_text_messages_callback else None,
        delivery_status_callback=delivery_status_callback['url'] if delivery_status_callback else None
    )


def get_delivery_status_callback_details():
    if current_service.service_callback_api:
        return service_api_client.get_service_callback_api(
            current_service.id,
            current_service.service_callback_api[0]
        )


@main.route("/services/<uuid:service_id>/api/callbacks/delivery-status-callback", methods=['GET', 'POST'])
@user_has_permissions('manage_api_keys')
def delivery_status_callback(service_id):
    delivery_status_callback = get_delivery_status_callback_details()
    back_link = (
        '.api_callbacks' if current_service.has_permission('inbound_sms')
        else '.api_integration'
    )

    form = CallbackForm(
        url=delivery_status_callback.get('url') if delivery_status_callback else '',
        bearer_token=dummy_bearer_token if delivery_status_callback else ''
    )

    if form.validate_on_submit():
        if delivery_status_callback and form.url.data:
            if (
                delivery_status_callback.get('url') != form.url.data or
                form.bearer_token.data != dummy_bearer_token
            ):
                service_api_client.update_service_callback_api(
                    service_id,
                    url=form.url.data,
                    bearer_token=check_token_against_dummy_bearer(form.bearer_token.data),
                    user_id=current_user.id,
                    callback_api_id=delivery_status_callback.get('id')
                )
        elif delivery_status_callback and not form.url.data:
            service_api_client.delete_service_callback_api(
                service_id,
                delivery_status_callback['id'],
            )
        elif form.url.data:
            service_api_client.create_service_callback_api(
                service_id,
                url=form.url.data,
                bearer_token=form.bearer_token.data,
                user_id=current_user.id
            )
        else:
            # If no callback is set up and the user chooses to continue
            # having no callback (ie both fields empty) then there’s
            # nothing for us to do here
            pass

        return redirect(url_for(back_link, service_id=service_id))

    return render_template(
        'views/api/callbacks/delivery-status-callback.html',
        back_link=back_link,
        form=form,
    )


def get_received_text_messages_callback():
    if current_service.inbound_api:
        return service_api_client.get_service_inbound_api(
            current_service.id,
            current_service.inbound_api[0]
        )


@main.route("/services/<uuid:service_id>/api/callbacks/received-text-messages-callback", methods=['GET', 'POST'])
@user_has_permissions('manage_api_keys')
def received_text_messages_callback(service_id):
    if not current_service.has_permission('inbound_sms'):
        return redirect(url_for('.api_integration', service_id=service_id))

    received_text_messages_callback = get_received_text_messages_callback()
    form = CallbackForm(
        url=received_text_messages_callback.get('url') if received_text_messages_callback else '',
        bearer_token=dummy_bearer_token if received_text_messages_callback else ''
    )

    if form.validate_on_submit():
        if received_text_messages_callback and form.url.data:
            if (
                received_text_messages_callback.get('url') != form.url.data or
                form.bearer_token.data != dummy_bearer_token
            ):
                service_api_client.update_service_inbound_api(
                    service_id,
                    url=form.url.data,
                    bearer_token=check_token_against_dummy_bearer(form.bearer_token.data),
                    user_id=current_user.id,
                    inbound_api_id=received_text_messages_callback.get('id')
                )
        elif received_text_messages_callback and not form.url.data:
            service_api_client.delete_service_inbound_api(
                service_id,
                received_text_messages_callback['id'],
            )
        elif form.url.data:
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
