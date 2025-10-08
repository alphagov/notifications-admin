from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from markupsafe import Markup
from notifications_utils.safe_string import make_string_safe

from app import (
    current_service,
    service_api_client,
)
from app.constants import ServiceCallbackTypes
from app.main import main
from app.main.forms import CallbackForm, CreateKeyForm, GuestList
from app.models.api_key import APIKey
from app.models.notification import APINotifications
from app.utils.user import user_has_permissions

dummy_bearer_token = "bearer_token_set"


@main.route("/services/<uuid:service_id>/api")
@user_has_permissions("manage_api_keys")
def api_integration(service_id):
    callbacks_link = ".api_callbacks" if current_service.can_have_multiple_callbacks else ".delivery_status_callback"

    return render_template(
        "views/api/index.html",
        callbacks_link=callbacks_link,
        api_notifications=APINotifications(service_id),
    )


@main.route("/services/<uuid:service_id>/api/documentation")
@user_has_permissions("manage_api_keys")
def api_documentation(service_id):
    return redirect(url_for(".guidance_api_documentation"), code=301)


@main.route(
    "/services/<uuid:service_id>/api/whitelist",
    methods=["GET", "POST"],
    endpoint="old_guest_list",
)
@main.route("/services/<uuid:service_id>/api/guest-list", methods=["GET", "POST"])
@user_has_permissions("manage_api_keys")
def guest_list(service_id):
    form = GuestList()
    if form.validate_on_submit():
        service_api_client.update_guest_list(
            service_id,
            {
                "email_addresses": list(filter(None, form.email_addresses.data)),
                "phone_numbers": list(filter(None, form.phone_numbers.data)),
            },
        )
        flash("Guest list updated", "default_with_tick")
        return redirect(url_for(".api_integration", service_id=service_id))
    if not form.errors:
        form.populate(**service_api_client.get_guest_list(service_id))
    return render_template("views/api/guest-list.html", form=form, error_summary_enabled=True)


@main.route("/services/<uuid:service_id>/api/keys")
@user_has_permissions("manage_api_keys")
def api_keys(service_id):
    return render_template("views/api/keys.html")


@main.route("/services/<uuid:service_id>/api/keys/create", methods=["GET", "POST"])
@user_has_permissions("manage_api_keys", restrict_admin_usage=True)
def create_api_key(service_id):
    form = CreateKeyForm(current_service.api_keys)
    form.key_type.choices = [
        (APIKey.TYPE_NORMAL, "Live – sends to anyone"),
        (APIKey.TYPE_TEAM, "Team and guest list – limits who you can send to"),
        (APIKey.TYPE_TEST, "Test – pretends to send messages"),
    ]
    # preserve order of items extended by starting with empty dicts
    form.key_type.param_extensions = {"items": [{}, {}]}
    if current_service.trial_mode:
        form.key_type.param_extensions["items"][0] = {
            "disabled": True,
            "hint": {
                "html": Markup(
                    "Not available because your service is in "
                    '<a class="govuk-link govuk-link--no-visited-state" href="/features/trial-mode">trial mode</a>'
                )
            },
        }
    if current_service.has_permission("letter"):
        form.key_type.param_extensions["items"][1]["hint"] = {"text": "Cannot be used to send letters"}
    if form.validate_on_submit():
        if current_service.trial_mode and form.key_type.data == APIKey.TYPE_NORMAL:
            abort(400)
        secret = APIKey.create(
            service_id=service_id,
            name=form.key_name.data,
            key_type=form.key_type.data,
        )
        return render_template(
            "views/api/keys/show.html",
            secret=secret,
            service_id=service_id,
            key_name=make_string_safe(form.key_name.data, whitespace="_"),
        )
    return render_template("views/api/keys/create.html", form=form, error_summary_enabled=True)


@main.route("/services/<uuid:service_id>/api/keys/revoke/<uuid:key_id>", methods=["GET", "POST"])
@user_has_permissions("manage_api_keys")
def revoke_api_key(service_id, key_id):
    key = current_service.api_keys.get(key_id)
    if request.method == "GET":
        flash(
            [
                f"Are you sure you want to revoke ‘{key.name}’?",
                "You will not be able to use this API key to connect to GOV.UK Notify.",
            ],
            "revoke this API key",
        )
        return render_template(
            "views/api/keys.html",
        )
    elif request.method == "POST":
        key.revoke(service_id=service_id)
        flash(f"‘{key.name}’ was revoked", "default_with_tick")
        return redirect(url_for(".api_keys", service_id=service_id))


def check_token_against_dummy_bearer(token):
    if token != dummy_bearer_token:
        return token
    else:
        return ""


@main.route("/services/<uuid:service_id>/api/callbacks", methods=["GET"])
@user_has_permissions("manage_api_keys")
def api_callbacks(service_id):
    if not current_service.can_have_multiple_callbacks:
        return redirect(url_for(".delivery_status_callback", service_id=service_id))

    return render_template("views/api/callbacks.html")


@main.route(
    "/services/<uuid:service_id>/api/callbacks/delivery-status-callback",
    methods=["GET", "POST"],
)
@user_has_permissions("manage_api_keys")
def delivery_status_callback(service_id):
    callback_details = current_service.delivery_status_callback_details
    back_link = ".api_callbacks" if current_service.can_have_multiple_callbacks else ".api_integration"

    form = CallbackForm(
        url=callback_details.get("url") if callback_details else "",
        bearer_token=dummy_bearer_token if callback_details else "",
    )
    callback_type = ServiceCallbackTypes.delivery_status.value

    if form.validate_on_submit():
        create_or_update_or_remove_callback(
            callback_details=callback_details, callback_type=callback_type, form=form, service_id=service_id
        )
        return redirect(url_for(back_link, service_id=service_id))

    return render_template(
        "views/api/callbacks/delivery-status-callback.html",
        back_link=back_link,
        form=form,
    )


@main.route(
    "/services/<uuid:service_id>/api/callbacks/received-text-messages-callback",
    methods=["GET", "POST"],
)
@user_has_permissions("manage_api_keys")
def received_text_messages_callback(service_id):
    if not current_service.has_permission("inbound_sms"):
        return redirect(url_for(".api_integration", service_id=service_id))

    callback_details = current_service.inbound_sms_callback_details
    form = CallbackForm(
        url=(callback_details.get("url") if callback_details else ""),
        bearer_token=dummy_bearer_token if callback_details else "",
    )
    callback_type = ServiceCallbackTypes.inbound_sms.value

    if form.validate_on_submit():
        create_or_update_or_remove_callback(
            callback_details=callback_details, callback_type=callback_type, form=form, service_id=service_id
        )
        return redirect(url_for(".api_callbacks", service_id=service_id))
    return render_template(
        "views/api/callbacks/received-text-messages-callback.html",
        form=form,
    )


@main.route(
    "/services/<uuid:service_id>/api/callbacks/returned-letters-callback",
    methods=["GET", "POST"],
)
@user_has_permissions("manage_api_keys")
def returned_letters_callback(service_id):
    callback_details = current_service.returned_letters_callback_details
    back_link = ".api_callbacks"

    form = CallbackForm(
        url=callback_details.get("url") if callback_details else "",
        bearer_token=dummy_bearer_token if callback_details else "",
    )
    callback_type = ServiceCallbackTypes.returned_letter.value

    if form.validate_on_submit():
        create_or_update_or_remove_callback(
            callback_details=callback_details, callback_type=callback_type, form=form, service_id=service_id
        )
        return redirect(url_for(back_link, service_id=service_id))

    return render_template(
        "views/api/callbacks/returned-letters-callback.html",
        back_link=back_link,
        form=form,
    )


def create_or_update_or_remove_callback(callback_details, callback_type, form, service_id):
    if callback_details and form.url.data:
        if callback_details.get("url") != form.url.data or form.bearer_token.data != dummy_bearer_token:
            service_api_client.update_service_callback_api(
                service_id,
                url=form.url.data,
                bearer_token=check_token_against_dummy_bearer(form.bearer_token.data),
                user_id=current_user.id,
                callback_api_id=callback_details.get("id"),
                callback_type=callback_type,
            )
    elif callback_details and not form.url.data:
        service_api_client.delete_service_callback_api(
            service_id=service_id,
            callback_api_id=callback_details["id"],
            callback_type=callback_type,
        )
    elif form.url.data:
        service_api_client.create_service_callback_api(
            service_id,
            url=form.url.data,
            bearer_token=form.bearer_token.data,
            user_id=current_user.id,
            callback_type=callback_type,
        )
    else:
        # If no callback is set up and the user chooses to continue
        # having no callback (ie both fields empty) then there’s
        # nothing for us to do here
        pass
