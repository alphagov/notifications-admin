from datetime import datetime

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from markupsafe import Markup
from notifications_python_client.errors import HTTPError
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime

from app import (
    billing_api_client,
    current_service,
    inbound_number_client,
    notification_api_client,
    organisations_client,
    service_api_client,
)
from app.constants import SIGN_IN_METHOD_TEXT_OR_EMAIL
from app.event_handlers import Events
from app.main import json_updates, main
from app.main.forms import (
    AdminBillingDetailsForm,
    AdminNotesForm,
    AdminPreviewBrandingForm,
    AdminServiceAddDataRetentionForm,
    AdminServiceEditDataRetentionForm,
    AdminServiceInboundNumberArchive,
    AdminServiceInboundNumberForm,
    AdminServiceMessageLimitForm,
    AdminServiceRateLimitForm,
    AdminServiceSMSAllowanceForm,
    AdminSetBrandingAddToBrandingPoolStepForm,
    AdminSetEmailBrandingForm,
    AdminSetLetterBrandingForm,
    AdminSetOrganisationForm,
    EstimateUsageForm,
    OnOffSettingForm,
    RenameServiceForm,
    SearchByNameForm,
    ServiceContactDetailsForm,
    ServiceEditInboundNumberForm,
    ServiceEmailSenderForm,
    ServiceLetterContactBlockForm,
    ServiceReplyToEmailForm,
    ServiceSmsSenderForm,
    ServiceSwitchChannelForm,
    SetAuthTypeForm,
    SetEmailAuthForUsersForm,
    SetServiceDataRetentionForm,
    SMSPrefixForm,
    YesNoSettingForm,
)
from app.models.branding import (
    AllEmailBranding,
    AllLetterBranding,
    EmailBranding,
    LetterBranding,
)
from app.models.letter_rates import LetterRates
from app.models.organisation import Organisation
from app.models.sms_rate import SMSRate
from app.utils import DELIVERED_STATUSES, FAILURE_STATUSES, SENDING_STATUSES
from app.utils.services import service_has_or_is_expected_to_send_x_or_more_notifications
from app.utils.user import user_has_permissions, user_is_platform_admin

PLATFORM_ADMIN_SERVICE_PERMISSIONS = {
    "inbound_sms": {"title": "Inkomende sms ontvangen", "requires": "sms", "endpoint": ".service_set_inbound_number"},
    "email_auth": {"title": "E-mailauthenticatie"},
    "sms_to_uk_landlines": {"title": "Sms-berichten naar Britse vaste nummers versturen"},
}


THANKS_FOR_BRANDING_REQUEST_MESSAGE = (
    "Bedankt voor uw aanvraag voor branding. We nemen uiterlijk aan het einde van de volgende werkdag contact met u op."
)


@main.route("/services/<uuid:service_id>/service-settings")
@user_has_permissions("manage_service", "manage_api_keys")
def service_settings(service_id):
    return render_template(
        "views/service-settings.html",
        service_permissions=PLATFORM_ADMIN_SERVICE_PERMISSIONS,
    )


@main.route("/services/<uuid:service_id>/service-settings/name", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_name_change(service_id):
    form = RenameServiceForm(name=current_service.name)

    if form.validate_on_submit():
        try:
            current_service.update(name=form.name.data, confirmed_unique=False)
        except HTTPError as http_error:
            if http_error.status_code == 400 and (
                error_message := service_api_client.parse_edit_service_http_error(http_error)
            ):
                form.name.errors.append(error_message)
            else:
                raise http_error
        else:
            return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/name.html",
        form=form,
        organisation_type=current_service.organisation_type,
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/service-settings/email-sender", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_email_sender_change(service_id):
    form = ServiceEmailSenderForm(
        use_custom_email_sender_name=current_service.custom_email_sender_name is not None,
        custom_email_sender_name=current_service.custom_email_sender_name,
    )

    if form.validate_on_submit():
        new_sender = form.custom_email_sender_name.data if form.use_custom_email_sender_name.data else None

        current_service.update(custom_email_sender_name=new_sender)

        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/custom-email-sender-name.html",
        form=form,
        organisation_type=current_service.organisation_type,
        error_summary_enabled=True,
    )


@main.post("/services/<uuid:service_id>/service-settings/email-sender/preview-address")
@user_has_permissions("manage_service")
def service_email_sender_preview(service_id):
    return jsonify(
        {
            "html": render_template(
                "partials/preview-email-sender-name.html",
                email_sender_name=request.form.get("custom_email_sender_name"),
            )
        }
    )


@main.route("/services/<uuid:service_id>/service-settings/set-data-retention", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_data_retention(service_id):
    high_volume_service = service_has_or_is_expected_to_send_x_or_more_notifications(
        current_service, num_notifications=1_000_000
    )
    single_retention_period = current_service.get_consistent_data_retention_period()
    form_kwargs = {"days_of_retention": single_retention_period} if single_retention_period else {}
    form = SetServiceDataRetentionForm(**form_kwargs)
    if not current_service.trial_mode and not high_volume_service and form.validate_on_submit():
        service_api_client.set_service_data_retention(
            service_id=service_id, days_of_retention=form.days_of_retention.data
        )
        flash(f"De bewaartermijn van gegevens is gewijzigd naar {form.days_of_retention.data} dagen", "default")
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/service-data-retention.html",
        form=form,
        high_volume_service=high_volume_service,
        single_retention_period=single_retention_period,
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/service-settings/request-to-go-live/estimate-usage", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def estimate_usage(service_id):
    form = EstimateUsageForm(
        volume_email=current_service.volume_email,
        volume_sms=current_service.volume_sms,
        volume_letter=current_service.volume_letter,
    )

    if form.validate_on_submit():
        current_service.update(
            volume_email=form.volume_email.data,
            volume_sms=form.volume_sms.data,
            volume_letter=form.volume_letter.data,
        )
        return redirect(
            url_for(
                "main.request_to_go_live",
                service_id=service_id,
            )
        )

    return render_template(
        "views/service-settings/estimate-usage.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/switch-live", methods=["GET", "POST"])
@user_is_platform_admin
def service_switch_live(service_id):
    if not current_service.active:
        abort(403)

    if current_service.trial_mode and (
        not current_service.organisation or current_service.organisation.agreement_signed is False
    ):
        abort(403)

    form = OnOffSettingForm(name="Make service live", enabled=not current_service.trial_mode)

    if form.validate_on_submit():
        current_service.update_status(live=form.enabled.data)
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-service-setting.html",
        title="Make service live",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/switch-count-as-live", methods=["GET", "POST"])
@user_is_platform_admin
def service_switch_count_as_live(service_id):
    form = YesNoSettingForm(
        name="Count in list of live services",
        enabled=current_service.count_as_live,
    )

    if form.validate_on_submit():
        current_service.update_count_as_live(form.enabled.data)
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-service-setting.html",
        title="Count in list of live services",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/permissions/<string:permission>", methods=["GET", "POST"])
@user_is_platform_admin
def service_set_permission(service_id, permission):
    if permission not in PLATFORM_ADMIN_SERVICE_PERMISSIONS:
        abort(404)

    title = PLATFORM_ADMIN_SERVICE_PERMISSIONS[permission]["title"]
    form = OnOffSettingForm(name=title, enabled=current_service.has_permission(permission))

    if form.validate_on_submit():
        current_service.force_permission(permission, on=form.enabled.data)

        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-service-setting.html",
        title=title,
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/archive", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def archive_service(service_id):
    if not current_service.active or not (current_service.trial_mode or current_user.platform_admin):
        abort(403)
    if request.method == "POST":
        # We need to purge the cache for the services users as otherwise, although they will have had their permissions
        # removed in the DB, they would still have permissions in the cache to view/edit/manage this service
        cached_service_user_ids = [user.id for user in current_service.active_users]

        service_api_client.archive_service(service_id, cached_service_user_ids)
        Events.archive_service(service_id=service_id, archived_by_id=current_user.id)

        flash(
            f"‘{current_service.name}’ is verwijderd",
            "default_with_tick",
        )
        return redirect(url_for(".your_services"))
    else:
        flash(
            Markup(
                render_template(
                    "partials/flash_messages/archive_service_confirmation_message.html",
                    service_name=current_service.name,
                    platform_admin=current_user.platform_admin,
                )
            ),
            "delete",
        )

        return service_settings(service_id)


@main.route("/services/<uuid:service_id>/service-settings/send-files-by-email", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def send_files_by_email_contact_details(service_id):
    form = ServiceContactDetailsForm()
    contact_details = None

    if request.method == "GET":
        contact_details = current_service.contact_link
        if contact_details:
            contact_type = check_contact_details_type(contact_details)
            field_to_update = getattr(form, contact_type)

            form.contact_details_type.data = contact_type
            field_to_update.data = contact_details

    if form.validate_on_submit():
        contact_type = form.contact_details_type.data

        current_service.update(contact_link=form.data[contact_type])
        return redirect(url_for(".service_settings", service_id=current_service.id))

    return render_template(
        "views/service-settings/send-files-by-email.html",
        form=form,
        contact_details=contact_details,
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-reply-to-email", methods=["GET"])
@user_has_permissions("manage_service")
def service_set_reply_to_email(service_id):
    return redirect(url_for(".service_email_reply_to", service_id=service_id))


@main.route("/services/<uuid:service_id>/service-settings/email-reply-to", methods=["GET"])
@user_has_permissions("manage_service", "manage_api_keys")
def service_email_reply_to(service_id):
    return render_template("views/service-settings/email_reply_to.html")


@main.route("/services/<uuid:service_id>/service-settings/email-reply-to/add", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_add_email_reply_to(service_id):
    form = ServiceReplyToEmailForm()
    first_email_address = current_service.count_email_reply_to_addresses == 0
    is_default = first_email_address if first_email_address else form.is_default.data

    if form.validate_on_submit():
        if current_user.platform_admin:
            try:
                service_api_client.add_reply_to_email_address(
                    service_id, email_address=form.email_address.data, is_default=is_default
                )

            except HTTPError as e:
                handle_reply_to_email_address_http_error(e, form)

            else:
                return redirect(url_for(".service_email_reply_to", service_id=service_id))

        else:
            try:
                notification_id = service_api_client.verify_reply_to_email_address(service_id, form.email_address.data)[
                    "data"
                ]["id"]
            except HTTPError as e:
                handle_reply_to_email_address_http_error(e, form)

            else:
                return redirect(
                    url_for(
                        ".service_verify_reply_to_address",
                        service_id=service_id,
                        notification_id=notification_id,
                        is_default=is_default,
                    )
                )

    return render_template(
        "views/service-settings/email-reply-to/add.html",
        form=form,
        first_email_address=first_email_address,
        error_summary_enabled=True,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:notification_id>/verify", methods=["GET", "POST"]
)
@user_has_permissions("manage_service")
def service_verify_reply_to_address(service_id, notification_id):
    replace = request.args.get("replace", False)
    is_default = request.args.get("is_default", False)
    return render_template(
        "views/service-settings/email-reply-to/verify.html",
        service_id=service_id,
        notification_id=notification_id,
        partials=get_service_verify_reply_to_address_partials(service_id, notification_id),
        replace=replace,
        is_default=is_default,
    )


@json_updates.route("/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:notification_id>/verify.json")
@user_has_permissions("manage_service")
def service_verify_reply_to_address_updates(service_id, notification_id):
    return jsonify(**get_service_verify_reply_to_address_partials(service_id, notification_id))


def get_service_verify_reply_to_address_partials(service_id, notification_id):
    form = ServiceReplyToEmailForm()
    first_email_address = current_service.count_email_reply_to_addresses == 0
    notification = notification_api_client.get_notification(current_app.config["NOTIFY_SERVICE_ID"], notification_id)
    replace = request.args.get("replace", False)
    replace = False if replace == "False" else replace
    existing_is_default = False
    if replace:
        existing = current_service.get_email_reply_to_address(replace)
        existing_is_default = existing["is_default"]
    verification_status = "pending"
    is_default = True if (request.args.get("is_default", False) == "True") else False
    if notification["status"] in DELIVERED_STATUSES:
        verification_status = "success"
        if notification["to"] not in [i["email_address"] for i in current_service.email_reply_to_addresses]:
            if replace:
                service_api_client.update_reply_to_email_address(
                    current_service.id, replace, email_address=notification["to"], is_default=is_default
                )
            else:
                service_api_client.add_reply_to_email_address(
                    current_service.id, email_address=notification["to"], is_default=is_default
                )
    seconds_since_sending = (
        utc_string_to_aware_gmt_datetime(datetime.utcnow().isoformat())
        - utc_string_to_aware_gmt_datetime(notification["created_at"])
    ).seconds
    if notification["status"] in FAILURE_STATUSES or (
        notification["status"] in SENDING_STATUSES
        and seconds_since_sending > current_app.config["REPLY_TO_EMAIL_ADDRESS_VALIDATION_TIMEOUT"]
    ):
        verification_status = "failure"
        form.email_address.data = notification["to"]
        form.is_default.data = is_default
    return {
        "status": render_template(
            "views/service-settings/email-reply-to/_verify-updates.html",
            reply_to_email_address=notification["to"],
            service_id=current_service.id,
            notification_id=notification_id,
            verification_status=verification_status,
            is_default=is_default,
            existing_is_default=existing_is_default,
            form=form,
            first_email_address=first_email_address,
            replace=replace,
        ),
        "stop": 0 if verification_status == "pending" else 1,
    }


@main.route(
    "/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:reply_to_email_id>/edit",
    methods=["GET", "POST"],
    endpoint="service_edit_email_reply_to",
)
@main.route(
    "/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:reply_to_email_id>/delete",
    methods=["GET"],
    endpoint="service_confirm_delete_email_reply_to",
)
@user_has_permissions("manage_service")
def service_edit_email_reply_to(service_id, reply_to_email_id):
    form = ServiceReplyToEmailForm()
    reply_to_email_address = current_service.get_email_reply_to_address(reply_to_email_id)
    if request.method == "GET":
        form.email_address.data = reply_to_email_address["email_address"]
        form.is_default.data = reply_to_email_address["is_default"]

    show_choice_of_default_checkbox = not reply_to_email_address["is_default"]

    if form.validate_on_submit():
        if form.email_address.data == reply_to_email_address["email_address"] or current_user.platform_admin:
            service_api_client.update_reply_to_email_address(
                current_service.id,
                reply_to_email_id=reply_to_email_id,
                email_address=form.email_address.data,
                is_default=True if reply_to_email_address["is_default"] else form.is_default.data,
            )
            return redirect(url_for(".service_email_reply_to", service_id=service_id))
        try:
            notification_id = service_api_client.verify_reply_to_email_address(service_id, form.email_address.data)[
                "data"
            ]["id"]

        except HTTPError as e:
            handle_reply_to_email_address_http_error(e, form)

        else:
            return redirect(
                url_for(
                    ".service_verify_reply_to_address",
                    service_id=service_id,
                    notification_id=notification_id,
                    is_default=True if reply_to_email_address["is_default"] else form.is_default.data,
                    replace=reply_to_email_id,
                )
            )

    if request.endpoint == "main.service_confirm_delete_email_reply_to":
        flash("Weet u zeker dat u dit reply-to e-mailadres wilt verwijderen?", "delete")
    return render_template(
        "views/service-settings/email-reply-to/edit.html",
        form=form,
        reply_to_email_address_id=reply_to_email_id,
        show_choice_of_default_checkbox=show_choice_of_default_checkbox,
        error_summary_enabled=True,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:reply_to_email_id>/delete", methods=["POST"]
)
@user_has_permissions("manage_service")
def service_delete_email_reply_to(service_id, reply_to_email_id):
    service_api_client.delete_reply_to_email_address(
        service_id=current_service.id,
        reply_to_email_id=reply_to_email_id,
    )
    return redirect(url_for(".service_email_reply_to", service_id=service_id))


@main.route("/services/<uuid:service_id>/service-settings/set-inbound-number", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_set_inbound_number(service_id):
    available_inbound_numbers = inbound_number_client.get_available_inbound_sms_numbers()
    inbound_numbers_value_and_label = [(number["id"], number["number"]) for number in available_inbound_numbers["data"]]
    no_available_numbers = available_inbound_numbers["data"] == []
    form = AdminServiceInboundNumberForm(inbound_number_choices=inbound_numbers_value_and_label)

    if form.validate_on_submit():
        inbound_number_client.add_inbound_number_to_service(
            current_service.id,
            inbound_number_id=form.inbound_number.data,
        )
        current_service.force_permission("inbound_sms", on=True)
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-inbound-number.html",
        form=form,
        no_available_numbers=no_available_numbers,
    )


@main.route("/services/<uuid:service_id>/service-settings/sms-prefix", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_set_sms_prefix(service_id):
    form = SMSPrefixForm(enabled=current_service.prefix_sms)

    form.enabled.label.text = f"Start all text messages with ‘{current_service.name}:’"

    if form.validate_on_submit():
        current_service.update(prefix_sms=form.enabled.data)
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template("views/service-settings/sms-prefix.html", form=form)


@main.route("/services/<uuid:service_id>/service-settings/set-international-sms", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_set_international_sms(service_id):
    form = OnOffSettingForm(
        "Send text messages to international phone numbers",
        enabled=current_service.has_permission("international_sms"),
    )
    if form.validate_on_submit():
        current_service.force_permission(
            "international_sms",
            on=form.enabled.data,
        )
        return redirect(url_for(".service_settings", service_id=service_id))
    return render_template(
        "views/service-settings/set-international-sms.html",
        form=form,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/set-message-limit/international-sms",
    methods=["GET", "POST"],
)
@user_has_permissions("manage_service")
def set_per_day_international_sms_message_limit(service_id):
    form = AdminServiceMessageLimitForm(
        message_limit=current_service.get_message_limit("international_sms"),
        notification_type="international_sms",
    )

    if form.validate_on_submit():
        current_service.update(international_sms_message_limit=form.message_limit.data)

        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-message-limit-for-international-sms.html",
        form=form,
        error_summary_enabled=True,
        partials=get_daily_limit_partials(daily_limit_type="international_sms"),
        updates_url=url_for(
            "json_updates.view_remaining_limit",
            service_id=service_id,
            daily_limit_type="international_sms",
        ),
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/daily-message-limit/<daily_limit_type:daily_limit_type>",
    methods=["GET"],
)
@user_has_permissions("manage_service")
def set_daily_message_limit(service_id, daily_limit_type):
    return render_template(
        "views/service-settings/daily-message-limit.html",
        daily_limit_type=daily_limit_type,
        partials=get_daily_limit_partials(daily_limit_type=daily_limit_type),
        updates_url=url_for(
            "json_updates.view_remaining_limit",
            service_id=service_id,
            daily_limit_type=daily_limit_type,
        ),
    )


@json_updates.route(
    "/services/<uuid:service_id>/service-settings/<daily_limit_type:daily_limit_type>/remaining-today.json"
)
@user_has_permissions("manage_service")
def view_remaining_limit(service_id, daily_limit_type):
    return jsonify(**get_daily_limit_partials(daily_limit_type=daily_limit_type))


def get_daily_limit_partials(daily_limit_type):
    return {
        "remaining_limit": render_template(
            "partials/daily-limits/remaining-limit.html", daily_limit_type=daily_limit_type
        ),
    }


@main.route("/services/<uuid:service_id>/service-settings/set-international-letters", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_set_international_letters(service_id):
    form = OnOffSettingForm(
        "Send letters to international addresses",
        enabled=current_service.has_permission("international_letters"),
    )
    if form.validate_on_submit():
        current_service.force_permission(
            "international_letters",
            on=form.enabled.data,
        )
        return redirect(url_for(".service_settings", service_id=service_id))
    return render_template(
        "views/service-settings/set-international-letters.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/receive-text-messages", methods=["GET"])
@user_has_permissions("manage_service")
def service_receive_text_messages(service_id):
    return render_template("views/service-settings/receive-text-messages.html")


@main.route("/services/<uuid:service_id>/service-settings/receive-text-messages/start", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_receive_text_messages_start(service_id):
    if current_service.has_permission("inbound_sms"):
        return redirect(url_for(".service_receive_text_messages", service_id=service_id))

    if request.method == "POST":
        sms_sender = inbound_number_client.add_inbound_number_to_service(current_service.id)
        current_service.force_permission("inbound_sms", on=True)
        Events.set_inbound_sms_on(
            user_id=current_user.id,
            service_id=current_service.id,
            inbound_number_id=sms_sender["inbound_number_id"],
        )

        flash("U heeft een telefoonnummer aan uw dienst toegevoegd.", "default_with_tick")
        return redirect(url_for(".service_receive_text_messages", service_id=service_id))

    return render_template("views/service-settings/receive-text-messages-start.html")


@main.route("/services/<uuid:service_id>/service-settings/receive-text-messages/stop", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_receive_text_messages_stop(service_id):
    if not current_service.has_permission("inbound_sms"):
        return redirect(url_for(".service_receive_text_messages", service_id=service_id))

    form = AdminServiceInboundNumberArchive()
    inbound_number = current_service.inbound_number

    if form.validate_on_submit():
        if current_service.default_sms_sender == current_service.inbound_number:
            form.removal_options.errors.append(
                "You need to change your default text message sender ID before you can continue"
            )

        else:
            archive = form.removal_options.data == "true"

            try:
                service_api_client.remove_service_inbound_sms(service_id, archive)
                return redirect(
                    url_for(
                        ".service_receive_text_messages_stop_success",
                        service_id=service_id,
                        inbound_number=inbound_number,
                    )
                )

            except Exception as e:
                current_app.logger.error(
                    "Error removing inbound number %s for service %s: %s", inbound_number, service_id, e
                )
                form.removal_options.errors.append("Failed to remove number from service")

    recent_use_date = None

    if current_user.platform_admin:
        resp = service_api_client.get_most_recent_inbound_number_usage_date(service_id)
        recent_use_date = resp["most_recent_date"]

    return render_template(
        "views/service-settings/receive-text-messages-stop.html",
        form=form,
        current_user=current_user,
        recent_use_date=recent_use_date,
    )


@main.route("/services/<uuid:service_id>/service-settings/receive-text-messages/stop/success", methods=["GET"])
@user_has_permissions("manage_service")
def service_receive_text_messages_stop_success(service_id):
    inbound_number = request.args.get("inbound_number", None)

    return render_template(
        "views/service-settings/receive-text-messages-stop-success.html",
        current_service=current_service,
        inbound_number=inbound_number,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-letters", methods=["GET"])
@user_has_permissions("manage_service")
def service_set_letters(service_id):
    return redirect(
        url_for(
            ".service_set_channel",
            service_id=current_service.id,
            channel="letter",
        ),
        code=301,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-<template_type:channel>", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_set_channel(service_id, channel):
    form = ServiceSwitchChannelForm(channel=channel, enabled=current_service.has_permission(channel))

    if form.validate_on_submit():
        current_service.force_permission(
            channel,
            on=form.enabled.data,
        )
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        f"views/service-settings/set-{channel}.html",
        form=form,
        sms_rate=SMSRate(),
        letter_rates=LetterRates().rates,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-auth-type", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_set_auth_type(service_id):
    form = SetAuthTypeForm(sign_in_method=current_service.sign_in_method)

    if current_service.sign_in_method == SIGN_IN_METHOD_TEXT_OR_EMAIL:
        if users_without_phone_numbers := [user for user in current_service.active_users if not user.mobile_number]:
            return render_template(
                "views/service-settings/disable-email-auth-blocked.html",
                users_without_phone_numbers=users_without_phone_numbers,
            )

    if form.validate_on_submit():
        if (
            current_service.sign_in_method == SIGN_IN_METHOD_TEXT_OR_EMAIL
            and form.sign_in_method.data != SIGN_IN_METHOD_TEXT_OR_EMAIL
        ):
            return redirect(url_for(".service_confirm_disable_email_auth", service_id=service_id))

        current_service.force_permission(
            "email_auth",
            on=form.sign_in_method.data == SIGN_IN_METHOD_TEXT_OR_EMAIL,
        )

        if form.sign_in_method.data == SIGN_IN_METHOD_TEXT_OR_EMAIL:
            return redirect(url_for(".service_set_auth_type_for_users", service_id=service_id))

        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-auth-type.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-auth-type/confirm", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_confirm_disable_email_auth(service_id):
    if current_service.sign_in_method != SIGN_IN_METHOD_TEXT_OR_EMAIL:
        return redirect(url_for(".service_set_auth_type", service_id=service_id))

    if any(not user.mobile_number for user in current_service.active_users):
        return redirect(url_for(".service_set_auth_type", service_id=service_id))

    if request.method == "POST":
        for user in current_service.active_users:
            if user.email_auth:
                user.update(auth_type="sms_auth")

        current_service.force_permission(
            "email_auth",
            on=False,
        )
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template("views/service-settings/confirm-disable-email-auth.html")


@main.route("/services/<uuid:service_id>/service-settings/set-auth-type/users", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_set_auth_type_for_users(service_id):
    if current_service.sign_in_method != SIGN_IN_METHOD_TEXT_OR_EMAIL:
        return redirect(url_for(".service_set_auth_type", service_id=service_id))

    all_service_users = [
        user
        for user in current_service.team_members
        if user.id != current_user.id and user.auth_type != "webauthn_auth"
    ]

    if not all_service_users:
        return redirect(url_for(".service_settings", service_id=service_id))

    form = SetEmailAuthForUsersForm(
        all_service_users=all_service_users, users=[user.id for user in all_service_users if user.email_auth]
    )

    if form.validate_on_submit():
        for user in all_service_users:
            should_use_email_auth = user.id in form.users.data
            new_auth_type = "email_auth" if should_use_email_auth else "sms_auth"

            if user.email_auth != should_use_email_auth:
                user.update(auth_type=new_auth_type)

        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template("views/service-settings/set-auth-type-for-users.html", form=form)


@main.route("/services/<uuid:service_id>/service-settings/letter-contacts", methods=["GET"])
@user_has_permissions("manage_service", "manage_api_keys")
def service_letter_contact_details(service_id):
    letter_contact_details = service_api_client.get_letter_contacts(service_id)
    return render_template(
        "views/service-settings/letter-contact-details.html", letter_contact_details=letter_contact_details
    )


@main.route("/services/<uuid:service_id>/service-settings/letter-contact/add", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_add_letter_contact(service_id):
    form = ServiceLetterContactBlockForm()
    first_contact_block = current_service.count_letter_contact_details == 0
    from_template = request.args.get("from_template")
    if form.validate_on_submit():
        new_letter_contact = service_api_client.add_letter_contact(
            current_service.id,
            contact_block=form.letter_contact_block.data.replace("\r", "") or None,
            is_default=first_contact_block if first_contact_block else form.is_default.data,
        )
        if from_template:
            service_api_client.update_service_template_sender(
                service_id,
                from_template,
                new_letter_contact["data"]["id"],
            )
            return redirect(url_for("main.view_template", service_id=service_id, template_id=from_template))
        return redirect(url_for(".service_letter_contact_details", service_id=service_id))
    return render_template(
        "views/service-settings/letter-contact/add.html",
        form=form,
        first_contact_block=first_contact_block,
        back_link=(
            url_for("main.view_template", template_id=from_template, service_id=current_service.id)
            if from_template
            else url_for(".service_letter_contact_details", service_id=current_service.id)
        ),
        error_summary_enabled=True,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/letter-contact/<uuid:letter_contact_id>/edit",
    methods=["GET", "POST"],
    endpoint="service_edit_letter_contact",
)
@main.route(
    "/services/<uuid:service_id>/service-settings/letter-contact/<uuid:letter_contact_id>/delete",
    methods=["GET"],
    endpoint="service_confirm_delete_letter_contact",
)
@user_has_permissions("manage_service")
def service_edit_letter_contact(service_id, letter_contact_id):
    letter_contact_block = current_service.get_letter_contact_block(letter_contact_id)
    form = ServiceLetterContactBlockForm(letter_contact_block=letter_contact_block["contact_block"])
    if request.method == "GET":
        form.is_default.data = letter_contact_block["is_default"]
    if form.validate_on_submit():
        current_service.edit_letter_contact_block(
            id=letter_contact_id,
            contact_block=form.letter_contact_block.data.replace("\r", "") or None,
            is_default=letter_contact_block["is_default"] or form.is_default.data,
        )
        return redirect(url_for(".service_letter_contact_details", service_id=service_id))

    if request.endpoint == "main.service_confirm_delete_letter_contact":
        flash("Weet u zeker dat u dit contactblok wilt verwijderen?", "delete")
    return render_template(
        "views/service-settings/letter-contact/edit.html",
        form=form,
        letter_contact_id=letter_contact_block["id"],
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/service-settings/letter-contact/make-blank-default")
@user_has_permissions("manage_service")
def service_make_blank_default_letter_contact(service_id):
    current_service.remove_default_letter_contact_block()
    return redirect(url_for(".service_letter_contact_details", service_id=service_id))


@main.route(
    "/services/<uuid:service_id>/service-settings/letter-contact/<uuid:letter_contact_id>/delete",
    methods=["POST"],
)
@user_has_permissions("manage_service")
def service_delete_letter_contact(service_id, letter_contact_id):
    service_api_client.delete_letter_contact(
        service_id=current_service.id,
        letter_contact_id=letter_contact_id,
    )
    return redirect(url_for(".service_letter_contact_details", service_id=current_service.id))


@main.route("/services/<uuid:service_id>/service-settings/sms-sender", methods=["GET"])
@user_has_permissions("manage_service", "manage_api_keys")
def service_sms_senders(service_id):
    return render_template(
        "views/service-settings/sms-senders.html",
    )


@main.route("/services/<uuid:service_id>/service-settings/sms-sender/add", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_add_sms_sender(service_id):
    form = ServiceSmsSenderForm()
    first_sms_sender = current_service.count_sms_senders == 0
    if form.validate_on_submit():
        service_api_client.add_sms_sender(
            current_service.id,
            sms_sender=form.sms_sender.data.replace("\r", "") or None,
            is_default=first_sms_sender if first_sms_sender else form.is_default.data,
        )
        return redirect(url_for(".service_sms_senders", service_id=service_id))
    return render_template(
        "views/service-settings/sms-sender/add.html",
        form=form,
        first_sms_sender=first_sms_sender,
        error_summary_enabled=True,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/sms-sender/<uuid:sms_sender_id>/edit",
    methods=["GET", "POST"],
    endpoint="service_edit_sms_sender",
)
@main.route(
    "/services/<uuid:service_id>/service-settings/sms-sender/<uuid:sms_sender_id>/delete",
    methods=["GET"],
    endpoint="service_confirm_delete_sms_sender",
)
@user_has_permissions("manage_service")
def service_edit_sms_sender(service_id, sms_sender_id):
    sms_sender = current_service.get_sms_sender(sms_sender_id)
    is_inbound_number = sms_sender["inbound_number_id"]
    if is_inbound_number:
        form = ServiceEditInboundNumberForm(is_default=sms_sender["is_default"])
    else:
        form = ServiceSmsSenderForm(**sms_sender)

    if form.validate_on_submit():
        service_api_client.update_sms_sender(
            current_service.id,
            sms_sender_id=sms_sender_id,
            sms_sender=sms_sender["sms_sender"] if is_inbound_number else form.sms_sender.data.replace("\r", ""),
            is_default=True if sms_sender["is_default"] else form.is_default.data,
        )
        return redirect(url_for(".service_sms_senders", service_id=service_id))

    form.is_default.data = sms_sender["is_default"]
    if request.endpoint == "main.service_confirm_delete_sms_sender":
        flash("Weet u zeker dat u deze sms-afzender-ID wilt verwijderen?", "delete")
    return render_template(
        "views/service-settings/sms-sender/edit.html",
        form=form,
        sms_sender=sms_sender,
        inbound_number=is_inbound_number,
        sms_sender_id=sms_sender_id,
        error_summary_enabled=True,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/sms-sender/<uuid:sms_sender_id>/delete",
    methods=["POST"],
)
@user_has_permissions("manage_service")
def service_delete_sms_sender(service_id, sms_sender_id):
    service_api_client.delete_sms_sender(
        service_id=current_service.id,
        sms_sender_id=sms_sender_id,
    )
    return redirect(url_for(".service_sms_senders", service_id=service_id))


@main.route("/services/<uuid:service_id>/service-settings/set-free-sms-allowance", methods=["GET", "POST"])
@user_is_platform_admin
def set_free_sms_allowance(service_id):
    form = AdminServiceSMSAllowanceForm(free_sms_allowance=current_service.free_sms_fragment_limit)

    if form.validate_on_submit():
        billing_api_client.create_or_update_free_sms_fragment_limit(service_id, form.free_sms_allowance.data)

        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template("views/service-settings/set-free-sms-allowance.html", form=form, error_summary_enabled=True)


@main.route(
    "/services/<uuid:service_id>/service-settings/set-message-limit/<template_type:notification_type>",
    methods=["GET", "POST"],
)
@user_is_platform_admin
def set_per_day_message_limit(service_id, notification_type):
    form = AdminServiceMessageLimitForm(
        message_limit=current_service.get_message_limit(notification_type),
        notification_type=notification_type,
    )

    if form.validate_on_submit():
        current_service.update(**{f"{notification_type}_message_limit": form.message_limit.data})

        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template("views/service-settings/set-message-limit.html", form=form, error_summary_enabled=True)


@main.route("/services/<uuid:service_id>/service-settings/set-rate-limit", methods=["GET", "POST"])
@user_is_platform_admin
def set_per_minute_rate_limit(service_id):
    form = AdminServiceRateLimitForm(rate_limit=current_service.rate_limit)

    if form.validate_on_submit():
        current_service.update(rate_limit=form.rate_limit.data)

        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template("views/service-settings/set-rate-limit.html", form=form, error_summary_enabled=True)


@main.route(
    "/services/<uuid:service_id>/service-settings/set-<branding_type:branding_type>-branding",
    methods=["GET", "POST"],
)
@user_is_platform_admin
def service_set_branding(service_id, branding_type):
    if branding_type == "email":
        form = AdminSetEmailBrandingForm(
            all_branding_options=AllEmailBranding().as_id_and_name,
            current_branding=current_service.email_branding_id,
        )

    elif branding_type == "letter":
        form = AdminSetLetterBrandingForm(
            all_branding_options=AllLetterBranding().as_id_and_name,
            current_branding=current_service.letter_branding_id,
        )

    if form.validate_on_submit():
        # As of 2022-12-02 we only get to this point (eg a POST on this endpoint) if JavaScript fails for the user on
        # this page. With JS enabled, the preview is shown as part of this view, and so the 'save' action skips the
        # separate preview page.
        return redirect(
            url_for(
                ".service_preview_branding",
                service_id=service_id,
                branding_type=branding_type,
                branding_style=form.branding_style.data,
            )
        )

    return render_template(
        "views/service-settings/set-branding.html",
        form=form,
        _search_form=SearchByNameForm(),
        branding_type=branding_type,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/set-<branding_type:branding_type>-branding/add-to-branding-pool-step",
    methods=["GET", "POST"],
)
@user_is_platform_admin
def service_set_branding_add_to_branding_pool_step(service_id, branding_type):
    branding_id = request.args.get("branding_id")

    if branding_type == "email":
        branding = EmailBranding.from_id(branding_id)
        add_brandings_to_pool = organisations_client.add_brandings_to_email_branding_pool

    elif branding_type == "letter":
        branding = LetterBranding.from_id(branding_id)
        add_brandings_to_pool = organisations_client.add_brandings_to_letter_branding_pool

    branding_name = branding.name
    org_id = current_service.organisation.id

    form = AdminSetBrandingAddToBrandingPoolStepForm()

    if form.validate_on_submit():
        # The service’s branding gets updated either way
        current_service.update(**{f"{branding_type}_branding": branding_id})
        message = f"De {branding_type}-branding is ingesteld op {branding_name}"

        # If the platform admin chose "yes" the branding is added to the organisation's branding pool
        if form.add_to_pool.data == "yes":
            branding_ids = [branding_id]
            add_brandings_to_pool(org_id, branding_ids)
            message = (
                f"De {branding_type}-branding is ingesteld op {branding_name} en toegevoegd aan "
                f"de {branding_type}-brandingpool van {current_service.organisation.name}"
            )

        flash(message, "default_with_tick")
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-branding-add-to-branding-pool-step.html",
        back_link=url_for(".service_set_branding", service_id=current_service.id, branding_type=branding_type),
        form=form,
        branding_name=branding_name,
        error_summary_enabled=True,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/preview-<branding_type:branding_type>-branding",
    methods=["GET", "POST"],
)
@user_is_platform_admin
def service_preview_branding(service_id, branding_type):
    branding_style = request.args.get("branding_style")

    if branding_type == "email":
        service_branding_pool = current_service.email_branding_pool

    elif branding_type == "letter":
        service_branding_pool = current_service.letter_branding_pool

    form = AdminPreviewBrandingForm(branding_style=branding_style)

    if form.validate_on_submit():
        branding_id = form.branding_style.data
        if branding_id == "__NONE__":  # This represents the email GOV.UK brand
            branding_id = None

        if current_service.organisation and branding_id and branding_id not in service_branding_pool.ids:
            return redirect(
                url_for(
                    "main.service_set_branding_add_to_branding_pool_step",
                    service_id=service_id,
                    branding_type=branding_type,
                    branding_id=branding_id,
                )
            )

        current_service.update(**{f"{branding_type}_branding": branding_id})
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/preview-branding.html",
        form=form,
        service_id=service_id,
        notification_type=branding_type,
        action=url_for("main.service_preview_branding", service_id=service_id, branding_type=branding_type),
    )


@main.route("/services/<uuid:service_id>/service-settings/link-service-to-organisation", methods=["GET", "POST"])
@user_is_platform_admin
def link_service_to_organisation(service_id):
    all_organisations = organisations_client.get_organisations()

    form = AdminSetOrganisationForm(
        choices=convert_dictionary_to_wtforms_choices_format(all_organisations, "id", "name"),
        organisations=current_service.organisation_id,
    )

    if form.validate_on_submit():
        if form.organisations.data != current_service.organisation_id:
            organisations_client.update_service_organisation(service_id, form.organisations.data)

            # if it's a GP in trial mode, we need to set their daily sms_message_limit to 0
            organisation = Organisation.from_id(form.organisations.data)
            if current_service.trial_mode and organisation.organisation_type == Organisation.TYPE_NHS_GP:
                current_service.update(sms_message_limit=0)

            current_service.update(has_active_go_live_request=False)
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/link-service-to-organisation.html",
        has_organisations=all_organisations,
        form=form,
        _search_form=SearchByNameForm(),
    )


@main.route("/services/<uuid:service_id>/data-retention", methods=["GET"])
@user_is_platform_admin
def data_retention(service_id):
    return render_template(
        "views/service-settings/data-retention.html",
    )


@main.route("/services/<uuid:service_id>/data-retention/add", methods=["GET", "POST"])
@user_is_platform_admin
def add_data_retention(service_id):
    form = AdminServiceAddDataRetentionForm()
    if form.validate_on_submit():
        service_api_client.create_service_data_retention(
            service_id, form.notification_type.data, form.days_of_retention.data
        )
        return redirect(url_for(".data_retention", service_id=service_id))
    return render_template(
        "views/service-settings/data-retention/add.html",
        form=form,
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/data-retention/<uuid:data_retention_id>/edit", methods=["GET", "POST"])
@user_is_platform_admin
def edit_data_retention(service_id, data_retention_id):
    data_retention_item = current_service.get_data_retention_item(data_retention_id)
    form = AdminServiceEditDataRetentionForm(days_of_retention=data_retention_item["days_of_retention"])
    if form.validate_on_submit():
        service_api_client.update_service_data_retention(service_id, data_retention_id, form.days_of_retention.data)
        return redirect(url_for(".data_retention", service_id=service_id))
    return render_template(
        "views/service-settings/data-retention/edit.html",
        form=form,
        data_retention_id=data_retention_id,
        notification_type=data_retention_item["notification_type"],
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/notes", methods=["GET", "POST"])
@user_is_platform_admin
def edit_service_notes(service_id):
    form = AdminNotesForm(notes=current_service.notes)

    if form.validate_on_submit():
        if form.notes.data == current_service.notes:
            return redirect(url_for(".service_settings", service_id=service_id))

        current_service.update(notes=form.notes.data)
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/edit-service-notes.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/edit-billing-details", methods=["GET", "POST"])
@user_is_platform_admin
def edit_service_billing_details(service_id):
    form = AdminBillingDetailsForm(
        billing_contact_email_addresses=current_service.billing_contact_email_addresses,
        billing_contact_names=current_service.billing_contact_names,
        billing_reference=current_service.billing_reference,
        purchase_order_number=current_service.purchase_order_number,
        notes=current_service.notes,
    )

    if form.validate_on_submit():
        current_service.update(
            billing_contact_email_addresses=form.billing_contact_email_addresses.data,
            billing_contact_names=form.billing_contact_names.data,
            billing_reference=form.billing_reference.data,
            purchase_order_number=form.purchase_order_number.data,
            notes=form.notes.data,
        )
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/edit-service-billing-details.html",
        form=form,
    )


def convert_dictionary_to_wtforms_choices_format(dictionary, value, label):
    return [(item[value], item[label]) for item in dictionary]


def check_contact_details_type(contact_details):
    if contact_details.startswith("http"):
        return "url"
    elif "@" in contact_details:
        return "email_address"
    else:
        return "phone_number"


def handle_reply_to_email_address_http_error(raised_exception, form):
    if raised_exception.status_code == 409:
        error_message = raised_exception.message
        form.email_address.errors.append(error_message)

    else:
        raise raised_exception
