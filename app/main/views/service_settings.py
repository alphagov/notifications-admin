from collections import OrderedDict
from datetime import datetime

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user
from notifications_python_client.errors import HTTPError

from app import (
    billing_api_client,
    current_service,
    email_branding_client,
    format_thousands,
    inbound_number_client,
    letter_branding_client,
    notification_api_client,
    organisations_client,
    service_api_client,
    user_api_client,
)
from app.extensions import zendesk_client
from app.main import main
from app.main.forms import (
    BrandingOptions,
    ConfirmPasswordForm,
    EstimateUsageForm,
    FreeSMSAllowance,
    InternationalSMSForm,
    LinkOrganisationsForm,
    PreviewBranding,
    RenameServiceForm,
    SearchByNameForm,
    ServiceContactDetailsForm,
    ServiceDataRetentionEditForm,
    ServiceDataRetentionForm,
    ServiceEditInboundNumberForm,
    ServiceInboundNumberForm,
    ServiceLetterContactBlockForm,
    ServiceOnOffSettingForm,
    ServiceReplyToEmailForm,
    ServiceSmsSenderForm,
    ServiceSwitchChannelForm,
    SetEmailBranding,
    SetLetterBranding,
    SMSPrefixForm,
)
from app.utils import (
    DELIVERED_STATUSES,
    FAILURE_STATUSES,
    SENDING_STATUSES,
    email_safe,
    user_has_permissions,
    user_is_gov_user,
    user_is_platform_admin,
)

PLATFORM_ADMIN_SERVICE_PERMISSIONS = OrderedDict([
    ('inbound_sms', {'title': 'Receive inbound SMS', 'requires': 'sms', 'endpoint': '.service_set_inbound_number'}),
    ('email_auth', {'title': 'Email authentication'}),
    ('upload_document', {'title': 'Send files by email', 'endpoint': '.service_switch_can_upload_document'}),
    ('upload_letters', {'title': 'Uploading letters', 'requires': 'letter'}),
])


@main.route("/services/<uuid:service_id>/service-settings")
@user_has_permissions('manage_service', 'manage_api_keys')
def service_settings(service_id):
    return render_template(
        'views/service-settings.html',
        service_permissions=PLATFORM_ADMIN_SERVICE_PERMISSIONS
    )


@main.route("/services/<uuid:service_id>/service-settings/name", methods=['GET', 'POST'])
@user_has_permissions('manage_service')
def service_name_change(service_id):
    form = RenameServiceForm()

    if request.method == 'GET':
        form.name.data = current_service.name

    if form.validate_on_submit():

        if form.name.data == current_service.name:
            return redirect(url_for('.service_settings', service_id=service_id))

        unique_name = service_api_client.is_service_name_unique(service_id, form.name.data, email_safe(form.name.data))

        if not unique_name:
            form.name.errors.append("This service name is already in use")
            return render_template('views/service-settings/name.html', form=form)

        session['service_name_change'] = form.name.data
        return redirect(url_for('.service_name_change_confirm', service_id=service_id))

    return render_template(
        'views/service-settings/name.html',
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/name/confirm", methods=['GET', 'POST'])
@user_has_permissions('manage_service')
def service_name_change_confirm(service_id):
    # Validate password for form
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)

    form = ConfirmPasswordForm(_check_password)

    if form.validate_on_submit():
        try:
            current_service.update(
                name=session['service_name_change'],
                email_from=email_safe(session['service_name_change'])
            )
        except HTTPError as e:
            error_msg = "Duplicate service name '{}'".format(session['service_name_change'])
            if e.status_code == 400 and error_msg in e.message['name']:
                # Redirect the user back to the change service name screen
                flash('This service name is already in use', 'error')
                return redirect(url_for('main.service_name_change', service_id=service_id))
            else:
                raise e
        else:
            session.pop('service_name_change')
            return redirect(url_for('.service_settings', service_id=service_id))
    return render_template(
        'views/service-settings/confirm.html',
        heading='Change your service name',
        form=form)


@main.route("/services/<uuid:service_id>/service-settings/request-to-go-live/estimate-usage", methods=['GET', 'POST'])
@user_has_permissions('manage_service')
def estimate_usage(service_id):

    form = EstimateUsageForm(
        volume_email=current_service.volume_email,
        volume_sms=current_service.volume_sms,
        volume_letter=current_service.volume_letter,
        consent_to_research={
            True: 'yes',
            False: 'no',
        }.get(current_service.consent_to_research),
    )

    if form.validate_on_submit():
        current_service.update(
            volume_email=form.volume_email.data,
            volume_sms=form.volume_sms.data,
            volume_letter=form.volume_letter.data,
            consent_to_research=(form.consent_to_research.data == 'yes'),
        )
        return redirect(url_for(
            'main.request_to_go_live',
            service_id=service_id,
        ))

    return render_template(
        'views/service-settings/estimate-usage.html',
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/request-to-go-live", methods=['GET'])
@user_has_permissions('manage_service')
def request_to_go_live(service_id):
    return render_template(
        'views/service-settings/request-to-go-live.html'
    )


@main.route("/services/<uuid:service_id>/service-settings/request-to-go-live", methods=['POST'])
@user_has_permissions('manage_service')
@user_is_gov_user
def submit_request_to_go_live(service_id):

    zendesk_client.create_ticket(
        subject='Request to go live - {}'.format(current_service.name),
        message=(
            'Service: {service_name}\n'
            '{service_dashboard}\n'
            '\n---'
            '\nOrganisation type: {organisation_type}'
            '\nAgreement signed: {agreement}'
            '\nEmails in next year: {volume_email_formatted}'
            '\nText messages in next year: {volume_sms_formatted}'
            '\nLetters in next year: {volume_letter_formatted}'
            '\nConsent to research: {research_consent}'
            '\nOther live services: {existing_live}'
            '\n'
            '\n---'
            '\nRequest sent by {email_address}'
            '\n'
        ).format(
            service_name=current_service.name,
            service_dashboard=url_for('main.service_dashboard', service_id=current_service.id, _external=True),
            organisation_type=str(current_service.organisation_type).title(),
            agreement=current_service.organisation.as_agreement_statement_for_go_live_request(
                current_user.email_domain
            ),
            volume_email_formatted=format_thousands(current_service.volume_email),
            volume_sms_formatted=format_thousands(current_service.volume_sms),
            volume_letter_formatted=format_thousands(current_service.volume_letter),
            research_consent='Yes' if current_service.consent_to_research else 'No',
            existing_live='Yes' if current_user.live_services else 'No',
            email_address=current_user.email_address,
        ),
        ticket_type=zendesk_client.TYPE_QUESTION,
        user_email=current_user.email_address,
        user_name=current_user.name,
        tags=current_service.request_to_go_live_tags,
    )

    current_service.update(go_live_user=current_user.id)

    flash('Thanks for your request to go live. We’ll get back to you within one working day.', 'default')
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<uuid:service_id>/service-settings/switch-live", methods=["GET", "POST"])
@user_is_platform_admin
def service_switch_live(service_id):
    form = ServiceOnOffSettingForm(
        name="Make service live",
        enabled=not current_service.trial_mode
    )

    if form.validate_on_submit():
        current_service.update_status(live=form.enabled.data)
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/set-service-setting.html',
        title="Make service live",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/switch-count-as-live", methods=["GET", "POST"])
@user_is_platform_admin
def service_switch_count_as_live(service_id):

    form = ServiceOnOffSettingForm(
        name="Count in list of live services",
        enabled=current_service.count_as_live,
        truthy='Yes',
        falsey='No',
    )

    if form.validate_on_submit():
        current_service.update_count_as_live(form.enabled.data)
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/set-service-setting.html',
        title="Count in list of live services",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/permissions/<permission>", methods=["GET", "POST"])
@user_is_platform_admin
def service_set_permission(service_id, permission):
    if permission not in PLATFORM_ADMIN_SERVICE_PERMISSIONS:
        abort(404)

    title = PLATFORM_ADMIN_SERVICE_PERMISSIONS[permission]['title']
    form = ServiceOnOffSettingForm(
        name=title,
        enabled=current_service.has_permission(permission)
    )

    if form.validate_on_submit():
        current_service.force_permission(permission, on=form.enabled.data)

        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        'views/service-settings/set-service-setting.html',
        title=title,
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/can-upload-document", methods=['GET', 'POST'])
@user_is_platform_admin
def service_switch_can_upload_document(service_id):
    if current_service.contact_link:
        return redirect(url_for('.service_set_permission', service_id=service_id, permission='upload_document'))

    form = ServiceContactDetailsForm()

    if form.validate_on_submit():
        contact_type = form.contact_details_type.data

        current_service.update(
            contact_link=form.data[contact_type]
        )

        return redirect(url_for('.service_set_permission', service_id=service_id, permission='upload_document'))

    return render_template('views/service-settings/contact_link.html', form=form)


@main.route("/services/<uuid:service_id>/service-settings/archive", methods=['GET', 'POST'])
@user_has_permissions('manage_service')
def archive_service(service_id):
    if not current_service.active and (
        current_service.trial_mode or current_user.platform_admin
    ):
        abort(403)
    if request.method == 'POST':
        service_api_client.archive_service(service_id)
        flash(
            '‘{}’ was deleted'.format(current_service.name),
            'default_with_tick',
        )
        return redirect(url_for('.choose_account'))
    else:
        flash(
            'Are you sure you want to delete ‘{}’? There’s no way to undo this.'.format(current_service.name),
            'delete',
        )
        return service_settings(service_id)


@main.route("/services/<uuid:service_id>/service-settings/suspend", methods=["GET", "POST"])
@user_has_permissions('manage_service')
def suspend_service(service_id):
    if request.method == 'POST':
        service_api_client.suspend_service(service_id)
        return redirect(url_for('.service_settings', service_id=service_id))
    else:
        flash("This will suspend the service and revoke all api keys. Are you sure you want to suspend this service?",
              'suspend')
        return service_settings(service_id)


@main.route("/services/<uuid:service_id>/service-settings/resume", methods=["GET", "POST"])
@user_has_permissions('manage_service')
def resume_service(service_id):
    if request.method == 'POST':
        service_api_client.resume_service(service_id)
        return redirect(url_for('.service_settings', service_id=service_id))
    else:
        flash("This will resume the service. New api key are required for this service to use the API.", 'resume')
        return service_settings(service_id)


@main.route("/services/<uuid:service_id>/service-settings/contact-link", methods=['GET', 'POST'])
@user_has_permissions('manage_service')
def service_set_contact_link(service_id):
    form = ServiceContactDetailsForm()

    if request.method == 'GET':
        contact_details = current_service.contact_link
        contact_type = check_contact_details_type(contact_details)
        field_to_update = getattr(form, contact_type)

        form.contact_details_type.data = contact_type
        field_to_update.data = contact_details

    if form.validate_on_submit():
        contact_type = form.contact_details_type.data

        current_service.update(
            contact_link=form.data[contact_type]
        )
        return redirect(url_for('.service_settings', service_id=current_service.id))

    return render_template('views/service-settings/contact_link.html', form=form)


@main.route("/services/<uuid:service_id>/service-settings/set-reply-to-email", methods=['GET'])
@user_has_permissions('manage_service')
def service_set_reply_to_email(service_id):
    return redirect(url_for('.service_email_reply_to', service_id=service_id))


@main.route("/services/<uuid:service_id>/service-settings/email-reply-to", methods=['GET'])
@user_has_permissions('manage_service', 'manage_api_keys')
def service_email_reply_to(service_id):
    return render_template('views/service-settings/email_reply_to.html')


@main.route("/services/<uuid:service_id>/service-settings/email-reply-to/add", methods=['GET', 'POST'])
@user_has_permissions('manage_service')
def service_add_email_reply_to(service_id):
    form = ServiceReplyToEmailForm()
    first_email_address = current_service.count_email_reply_to_addresses == 0
    is_default = first_email_address if first_email_address else form.is_default.data
    if form.validate_on_submit():
        try:
            notification_id = service_api_client.verify_reply_to_email_address(
                service_id, form.email_address.data
            )["data"]["id"]
        except HTTPError as e:
            error_msg = "Your service already uses '{}' as an email reply-to address.".format(form.email_address.data)
            if e.status_code == 400 and error_msg == e.message:
                flash(error_msg, 'error')
                return redirect(url_for('.service_email_reply_to', service_id=service_id))
            else:
                raise e
        return redirect(url_for(
            '.service_verify_reply_to_address',
            service_id=service_id,
            notification_id=notification_id,
            is_default=is_default
        ))

    return render_template(
        'views/service-settings/email-reply-to/add.html',
        form=form,
        first_email_address=first_email_address)


@main.route(
    "/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:notification_id>/verify",
    methods=['GET', 'POST']
)
@user_has_permissions('manage_service')
def service_verify_reply_to_address(service_id, notification_id):
    replace = request.args.get('replace', False)
    is_default = request.args.get('is_default', False)
    return render_template(
        'views/service-settings/email-reply-to/verify.html',
        service_id=service_id,
        notification_id=notification_id,
        partials=get_service_verify_reply_to_address_partials(service_id, notification_id),
        verb=("Change" if replace else "Add"),
        replace=replace,
        is_default=is_default
    )


@main.route("/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:notification_id>/verify.json")
@user_has_permissions('manage_service')
def service_verify_reply_to_address_updates(service_id, notification_id):
    return jsonify(**get_service_verify_reply_to_address_partials(service_id, notification_id))


def get_service_verify_reply_to_address_partials(service_id, notification_id):
    form = ServiceReplyToEmailForm()
    first_email_address = current_service.count_email_reply_to_addresses == 0
    notification = notification_api_client.get_notification(current_app.config["NOTIFY_SERVICE_ID"], notification_id)
    replace = request.args.get('replace', False)
    replace = False if replace == "False" else replace
    existing_is_default = False
    if replace:
        existing = current_service.get_email_reply_to_address(replace)
        existing_is_default = existing['is_default']
    verification_status = "pending"
    is_default = True if (request.args.get('is_default', False) == "True") else False
    if notification["status"] in DELIVERED_STATUSES:
        verification_status = "success"
        if notification["to"] not in [i["email_address"] for i in current_service.email_reply_to_addresses]:
            if replace:
                service_api_client.update_reply_to_email_address(
                    current_service.id, replace, email_address=notification["to"], is_default=is_default
                )
            else:
                service_api_client.add_reply_to_email_address(
                    current_service.id,
                    email_address=notification["to"],
                    is_default=is_default
                )
    created_at_no_tz = notification["created_at"][:-6]
    seconds_since_sending = (datetime.utcnow() - datetime.strptime(created_at_no_tz, '%Y-%m-%dT%H:%M:%S.%f')).seconds
    if notification["status"] in FAILURE_STATUSES or (
        notification["status"] in SENDING_STATUSES and
        seconds_since_sending > current_app.config['REPLY_TO_EMAIL_ADDRESS_VALIDATION_TIMEOUT']
    ):
        verification_status = "failure"
        form.email_address.data = notification['to']
        form.is_default.data = is_default
    return {
        'status': render_template(
            'views/service-settings/email-reply-to/_verify-updates.html',
            reply_to_email_address=notification["to"],
            service_id=current_service.id,
            notification_id=notification_id,
            verification_status=verification_status,
            is_default=is_default,
            existing_is_default=existing_is_default,
            form=form,
            first_email_address=first_email_address,
            replace=replace
        ),
        'stop': 0 if verification_status == "pending" else 1
    }


@main.route(
    "/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:reply_to_email_id>/edit",
    methods=['GET', 'POST'],
    endpoint="service_edit_email_reply_to"
)
@main.route(
    "/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:reply_to_email_id>/delete",
    methods=['GET'],
    endpoint="service_confirm_delete_email_reply_to"
)
@user_has_permissions('manage_service')
def service_edit_email_reply_to(service_id, reply_to_email_id):
    form = ServiceReplyToEmailForm()
    reply_to_email_address = current_service.get_email_reply_to_address(reply_to_email_id)
    if request.method == 'GET':
        form.email_address.data = reply_to_email_address['email_address']
        form.is_default.data = reply_to_email_address['is_default']
    if form.validate_on_submit():
        if form.email_address.data == reply_to_email_address["email_address"]:
            service_api_client.update_reply_to_email_address(
                current_service.id,
                reply_to_email_id=reply_to_email_id,
                email_address=form.email_address.data,
                is_default=True if reply_to_email_address['is_default'] else form.is_default.data
            )
            return redirect(url_for('.service_email_reply_to', service_id=service_id))
        try:
            notification_id = service_api_client.verify_reply_to_email_address(
                service_id, form.email_address.data
            )["data"]["id"]
        except HTTPError as e:
            error_msg = "Your service already uses ‘{}’ as a reply-to email address.".format(form.email_address.data)
            if e.status_code == 400 and error_msg == e.message:
                flash(error_msg, 'error')
                return redirect(url_for('.service_email_reply_to', service_id=service_id))
            else:
                raise e
        return redirect(url_for(
            '.service_verify_reply_to_address',
            service_id=service_id,
            notification_id=notification_id,
            is_default=True if reply_to_email_address['is_default'] else form.is_default.data,
            replace=reply_to_email_id
        ))

    if (request.endpoint == "main.service_confirm_delete_email_reply_to"):
        flash("Are you sure you want to delete this reply-to email address?", 'delete')
    return render_template(
        'views/service-settings/email-reply-to/edit.html',
        form=form,
        reply_to_email_address_id=reply_to_email_id,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:reply_to_email_id>/delete",
    methods=['POST']
)
@user_has_permissions('manage_service')
def service_delete_email_reply_to(service_id, reply_to_email_id):
    service_api_client.delete_reply_to_email_address(
        service_id=current_service.id,
        reply_to_email_id=reply_to_email_id,
    )
    return redirect(url_for('.service_email_reply_to', service_id=service_id))


@main.route("/services/<uuid:service_id>/service-settings/set-inbound-number", methods=['GET', 'POST'])
@user_has_permissions('manage_service')
def service_set_inbound_number(service_id):
    available_inbound_numbers = inbound_number_client.get_available_inbound_sms_numbers()
    inbound_numbers_value_and_label = [
        (number['id'], number['number']) for number in available_inbound_numbers['data']
    ]
    no_available_numbers = available_inbound_numbers['data'] == []
    form = ServiceInboundNumberForm(
        inbound_number_choices=inbound_numbers_value_and_label
    )

    if form.validate_on_submit():
        service_api_client.add_sms_sender(
            current_service.id,
            sms_sender=form.inbound_number.data,
            is_default=True,
            inbound_number_id=form.inbound_number.data
        )
        current_service.force_permission('inbound_sms', on=True)
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/set-inbound-number.html',
        form=form,
        no_available_numbers=no_available_numbers,
    )


@main.route("/services/<uuid:service_id>/service-settings/sms-prefix", methods=['GET', 'POST'])
@user_has_permissions('manage_service')
def service_set_sms_prefix(service_id):

    form = SMSPrefixForm(enabled=(
        'on' if current_service.prefix_sms else 'off'
    ))

    form.enabled.label.text = 'Start all text messages with ‘{}:’'.format(current_service.name)

    if form.validate_on_submit():
        current_service.update(
            prefix_sms=(form.enabled.data == 'on')
        )
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/sms-prefix.html',
        form=form
    )


@main.route("/services/<uuid:service_id>/service-settings/set-international-sms", methods=['GET', 'POST'])
@user_has_permissions('manage_service')
def service_set_international_sms(service_id):
    form = InternationalSMSForm(
        enabled='on' if current_service.has_permission('international_sms') else 'off'
    )
    if form.validate_on_submit():
        current_service.force_permission(
            'international_sms',
            on=(form.enabled.data == 'on'),
        )
        return redirect(
            url_for(".service_settings", service_id=service_id)
        )
    return render_template(
        'views/service-settings/set-international-sms.html',
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-inbound-sms", methods=['GET'])
@user_has_permissions('manage_service')
def service_set_inbound_sms(service_id):
    return render_template(
        'views/service-settings/set-inbound-sms.html',
    )


@main.route("/services/<uuid:service_id>/service-settings/set-letters", methods=['GET'])
@user_has_permissions('manage_service')
def service_set_letters(service_id):
    return redirect(
        url_for(
            '.service_set_channel',
            service_id=current_service.id,
            channel='letter',
        ),
        code=301,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-<channel>", methods=['GET', 'POST'])
@user_has_permissions('manage_service')
def service_set_channel(service_id, channel):

    if channel not in {'email', 'sms', 'letter'}:
        abort(404)

    form = ServiceSwitchChannelForm(
        channel=channel,
        enabled=current_service.has_permission(channel)
    )

    if form.validate_on_submit():
        current_service.force_permission(
            channel,
            on=form.enabled.data,
        )
        return redirect(
            url_for(".service_settings", service_id=service_id)
        )

    return render_template(
        'views/service-settings/set-{}.html'.format(channel),
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-auth-type", methods=['GET'])
@user_has_permissions('manage_service')
def service_set_auth_type(service_id):
    return render_template(
        'views/service-settings/set-auth-type.html',
    )


@main.route("/services/<uuid:service_id>/service-settings/letter-contacts", methods=['GET'])
@user_has_permissions('manage_service', 'manage_api_keys')
def service_letter_contact_details(service_id):
    letter_contact_details = service_api_client.get_letter_contacts(service_id)
    return render_template(
        'views/service-settings/letter-contact-details.html',
        letter_contact_details=letter_contact_details)


@main.route("/services/<uuid:service_id>/service-settings/letter-contact/add", methods=['GET', 'POST'])
@user_has_permissions('manage_service')
def service_add_letter_contact(service_id):
    form = ServiceLetterContactBlockForm()
    first_contact_block = current_service.count_letter_contact_details == 0
    from_template = request.args.get('from_template')
    if form.validate_on_submit():
        new_letter_contact = service_api_client.add_letter_contact(
            current_service.id,
            contact_block=form.letter_contact_block.data.replace('\r', '') or None,
            is_default=first_contact_block if first_contact_block else form.is_default.data
        )
        if from_template:
            service_api_client.update_service_template_sender(
                service_id,
                from_template,
                new_letter_contact['data']['id'],
            )
            return redirect(
                url_for('.view_template', service_id=service_id, template_id=from_template)
            )
        return redirect(url_for('.service_letter_contact_details', service_id=service_id))
    return render_template(
        'views/service-settings/letter-contact/add.html',
        form=form,
        first_contact_block=first_contact_block,
        back_link=(
            url_for('main.view_template', template_id=from_template, service_id=current_service.id)
            if from_template
            else url_for('.service_letter_contact_details', service_id=current_service.id)
        ),
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/letter-contact/<uuid:letter_contact_id>/edit",
    methods=['GET', 'POST'],
    endpoint="service_edit_letter_contact",
)
@main.route(
    "/services/<uuid:service_id>/service-settings/letter-contact/<uuid:letter_contact_id>/delete",
    methods=['GET'],
    endpoint="service_confirm_delete_letter_contact",
)
@user_has_permissions('manage_service')
def service_edit_letter_contact(service_id, letter_contact_id):
    letter_contact_block = current_service.get_letter_contact_block(letter_contact_id)
    form = ServiceLetterContactBlockForm(
        letter_contact_block=letter_contact_block['contact_block']
    )
    if request.method == 'GET':
        form.is_default.data = letter_contact_block['is_default']
    if form.validate_on_submit():
        current_service.edit_letter_contact_block(
            id=letter_contact_id,
            contact_block=form.letter_contact_block.data.replace('\r', '') or None,
            is_default=letter_contact_block['is_default'] or form.is_default.data
        )
        return redirect(url_for('.service_letter_contact_details', service_id=service_id))

    if (request.endpoint == "main.service_confirm_delete_letter_contact"):
        flash("Are you sure you want to delete this contact block?", 'delete')
    return render_template(
        'views/service-settings/letter-contact/edit.html',
        form=form,
        letter_contact_id=letter_contact_block['id'])


@main.route("/services/<uuid:service_id>/service-settings/letter-contact/make-blank-default")
@user_has_permissions('manage_service')
def service_make_blank_default_letter_contact(service_id):
    current_service.remove_default_letter_contact_block()
    return redirect(url_for('.service_letter_contact_details', service_id=service_id))


@main.route(
    "/services/<uuid:service_id>/service-settings/letter-contact/<uuid:letter_contact_id>/delete",
    methods=['POST'],
)
@user_has_permissions('manage_service')
def service_delete_letter_contact(service_id, letter_contact_id):
    service_api_client.delete_letter_contact(
        service_id=current_service.id,
        letter_contact_id=letter_contact_id,
    )
    return redirect(url_for('.service_letter_contact_details', service_id=current_service.id))


@main.route("/services/<uuid:service_id>/service-settings/sms-sender", methods=['GET'])
@user_has_permissions('manage_service', 'manage_api_keys')
def service_sms_senders(service_id):
    return render_template(
        'views/service-settings/sms-senders.html',
    )


@main.route("/services/<uuid:service_id>/service-settings/sms-sender/add", methods=['GET', 'POST'])
@user_has_permissions('manage_service')
def service_add_sms_sender(service_id):
    form = ServiceSmsSenderForm()
    first_sms_sender = current_service.count_sms_senders == 0
    if form.validate_on_submit():
        service_api_client.add_sms_sender(
            current_service.id,
            sms_sender=form.sms_sender.data.replace('\r', '') or None,
            is_default=first_sms_sender if first_sms_sender else form.is_default.data
        )
        return redirect(url_for('.service_sms_senders', service_id=service_id))
    return render_template(
        'views/service-settings/sms-sender/add.html',
        form=form,
        first_sms_sender=first_sms_sender)


@main.route(
    "/services/<uuid:service_id>/service-settings/sms-sender/<uuid:sms_sender_id>/edit",
    methods=['GET', 'POST'],
    endpoint="service_edit_sms_sender"
)
@main.route(
    "/services/<uuid:service_id>/service-settings/sms-sender/<uuid:sms_sender_id>/delete",
    methods=['GET'],
    endpoint="service_confirm_delete_sms_sender"
)
@user_has_permissions('manage_service')
def service_edit_sms_sender(service_id, sms_sender_id):
    sms_sender = current_service.get_sms_sender(sms_sender_id)
    is_inbound_number = sms_sender['inbound_number_id']
    if is_inbound_number:
        form = ServiceEditInboundNumberForm(is_default=sms_sender['is_default'])
    else:
        form = ServiceSmsSenderForm(**sms_sender)

    if form.validate_on_submit():
        service_api_client.update_sms_sender(
            current_service.id,
            sms_sender_id=sms_sender_id,
            sms_sender=sms_sender['sms_sender'] if is_inbound_number else form.sms_sender.data.replace('\r', ''),
            is_default=True if sms_sender['is_default'] else form.is_default.data
        )
        return redirect(url_for('.service_sms_senders', service_id=service_id))

    form.is_default.data = sms_sender['is_default']
    if (request.endpoint == "main.service_confirm_delete_sms_sender"):
        flash("Are you sure you want to delete this text message sender?", 'delete')
    return render_template(
        'views/service-settings/sms-sender/edit.html',
        form=form,
        sms_sender=sms_sender,
        inbound_number=is_inbound_number,
        sms_sender_id=sms_sender_id
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/sms-sender/<uuid:sms_sender_id>/delete",
    methods=['POST'],
)
@user_has_permissions('manage_service')
def service_delete_sms_sender(service_id, sms_sender_id):
    service_api_client.delete_sms_sender(
        service_id=current_service.id,
        sms_sender_id=sms_sender_id,
    )
    return redirect(url_for('.service_sms_senders', service_id=service_id))


@main.route("/services/<uuid:service_id>/service-settings/set-letter-contact-block", methods=['GET', 'POST'])
@user_has_permissions('manage_service')
def service_set_letter_contact_block(service_id):

    if not current_service.has_permission('letter'):
        abort(403)

    form = ServiceLetterContactBlockForm(letter_contact_block=current_service.letter_contact_block)
    if form.validate_on_submit():
        current_service.update(
            letter_contact_block=form.letter_contact_block.data.replace('\r', '') or None
        )
        if request.args.get('from_template'):
            return redirect(
                url_for('.view_template', service_id=service_id, template_id=request.args.get('from_template'))
            )
        return redirect(url_for('.service_settings', service_id=service_id))
    return render_template(
        'views/service-settings/set-letter-contact-block.html',
        form=form
    )


@main.route("/services/<uuid:service_id>/service-settings/set-free-sms-allowance", methods=['GET', 'POST'])
@user_is_platform_admin
def set_free_sms_allowance(service_id):

    form = FreeSMSAllowance(free_sms_allowance=current_service.free_sms_fragment_limit)

    if form.validate_on_submit():
        billing_api_client.create_or_update_free_sms_fragment_limit(service_id, form.free_sms_allowance.data)

        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/set-free-sms-allowance.html',
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-email-branding", methods=['GET', 'POST'])
@user_is_platform_admin
def service_set_email_branding(service_id):
    email_branding = email_branding_client.get_all_email_branding()

    form = SetEmailBranding(
        all_branding_options=get_branding_as_value_and_label(email_branding),
        current_branding=current_service.email_branding_id,
    )

    if form.validate_on_submit():
        return redirect(url_for(
            '.service_preview_email_branding',
            service_id=service_id,
            branding_style=form.branding_style.data,
        ))

    return render_template(
        'views/service-settings/set-email-branding.html',
        form=form,
        search_form=SearchByNameForm()
    )


@main.route("/services/<uuid:service_id>/service-settings/preview-email-branding", methods=['GET', 'POST'])
@user_is_platform_admin
def service_preview_email_branding(service_id):
    branding_style = request.args.get('branding_style', None)

    form = PreviewBranding(branding_style=branding_style)

    if form.validate_on_submit():
        current_service.update(
            email_branding=form.branding_style.data
        )
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/preview-email-branding.html',
        form=form,
        service_id=service_id,
        action=url_for('main.service_preview_email_branding', service_id=service_id),
    )


@main.route("/services/<uuid:service_id>/service-settings/set-letter-branding", methods=['GET', 'POST'])
@user_is_platform_admin
def service_set_letter_branding(service_id):
    letter_branding = letter_branding_client.get_all_letter_branding()

    form = SetLetterBranding(
        all_branding_options=get_branding_as_value_and_label(letter_branding),
        current_branding=current_service.letter_branding_id,
    )

    if form.validate_on_submit():
        return redirect(url_for(
            '.service_preview_letter_branding',
            service_id=service_id,
            branding_style=form.branding_style.data,
        ))

    return render_template(
        'views/service-settings/set-letter-branding.html',
        form=form,
        search_form=SearchByNameForm()
    )


@main.route("/services/<uuid:service_id>/service-settings/preview-letter-branding", methods=['GET', 'POST'])
@user_is_platform_admin
def service_preview_letter_branding(service_id):
    branding_style = request.args.get('branding_style')

    form = PreviewBranding(branding_style=branding_style)

    if form.validate_on_submit():
        current_service.update(
            letter_branding=form.branding_style.data
        )
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/preview-letter-branding.html',
        form=form,
        service_id=service_id,
        action=url_for('main.service_preview_letter_branding', service_id=service_id),
    )


@main.route("/services/<uuid:service_id>/service-settings/link-service-to-organisation", methods=['GET', 'POST'])
@user_is_platform_admin
def link_service_to_organisation(service_id):

    all_organisations = organisations_client.get_organisations()
    current_linked_organisation = organisations_client.get_service_organisation(service_id).get('id', None)

    form = LinkOrganisationsForm(
        choices=convert_dictionary_to_wtforms_choices_format(all_organisations, 'id', 'name'),
        organisations=current_linked_organisation
    )

    if form.validate_on_submit():
        if form.organisations.data != current_linked_organisation:
            organisations_client.update_service_organisation(
                service_id,
                form.organisations.data
            )
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/link-service-to-organisation.html',
        has_organisations=all_organisations,
        form=form,
        search_form=SearchByNameForm(),
    )


@main.route("/services/<uuid:service_id>/branding-request/<branding_type>", methods=['GET', 'POST'])
@user_has_permissions('manage_service')
def branding_request(service_id, branding_type):
    form = BrandingOptions(current_service, branding_type=branding_type)
    from_template = request.args.get('from_template')
    if branding_type == "email":
        branding_name = current_service.email_branding_name
    elif branding_type == "letter":
        branding_name = current_service.letter_branding_name
    if form.validate_on_submit():
        zendesk_client.create_ticket(
            subject='{} branding request - {}'.format(branding_type.capitalize(), current_service.name),
            message=(
                'Organisation: {organisation}\n'
                'Service: {service_name}\n'
                '{dashboard_url}\n'
                '\n---'
                '\nCurrent branding: {current_branding}'
                '\nBranding requested: {branding_requested}'
                '{new_paragraph}'
                '{detail}'
                '\n'
            ).format(
                organisation=current_service.organisation.as_info_for_branding_request(current_user.email_domain),
                service_name=current_service.name,
                dashboard_url=url_for('main.service_dashboard', service_id=current_service.id, _external=True),
                current_branding=branding_name,
                branding_requested=dict(form.options.choices)[form.options.data],
                new_paragraph='\n\n' if form.something_else.data else '',
                detail=form.something_else.data or ''
            ),
            ticket_type=zendesk_client.TYPE_QUESTION,
            user_email=current_user.email_address,
            user_name=current_user.name,
            tags=['notify_action', 'notify_branding'],
        )
        flash((
            'Thanks for your branding request. We’ll get back to you '
            'within one working day.'
        ), 'default')
        return redirect(url_for(
            '.view_template', service_id=current_service.id, template_id=from_template
        ) if from_template else url_for('.service_settings', service_id=current_service.id))

    return render_template(
        'views/service-settings/branding/branding-options.html',
        form=form,
        branding_type=branding_type,
        branding_name=branding_name,
        from_template=from_template
    )


@main.route("/services/<uuid:service_id>/data-retention", methods=['GET'])
@user_is_platform_admin
def data_retention(service_id):
    return render_template(
        'views/service-settings/data-retention.html',
    )


@main.route("/services/<uuid:service_id>/data-retention/add", methods=['GET', 'POST'])
@user_is_platform_admin
def add_data_retention(service_id):
    form = ServiceDataRetentionForm()
    if form.validate_on_submit():
        service_api_client.create_service_data_retention(service_id,
                                                         form.notification_type.data,
                                                         form.days_of_retention.data)
        return redirect(url_for('.data_retention', service_id=service_id))
    return render_template(
        'views/service-settings/data-retention/add.html',
        form=form
    )


@main.route("/services/<uuid:service_id>/data-retention/<uuid:data_retention_id>/edit", methods=['GET', 'POST'])
@user_is_platform_admin
def edit_data_retention(service_id, data_retention_id):
    data_retention_item = current_service.get_data_retention_item(data_retention_id)
    form = ServiceDataRetentionEditForm(days_of_retention=data_retention_item['days_of_retention'])
    if form.validate_on_submit():
        service_api_client.update_service_data_retention(service_id, data_retention_id, form.days_of_retention.data)
        return redirect(url_for('.data_retention', service_id=service_id))
    return render_template(
        'views/service-settings/data-retention/edit.html',
        form=form,
        data_retention_id=data_retention_id,
        notification_type=data_retention_item['notification_type']
    )


def get_branding_as_value_and_label(email_branding):
    return [
        (branding['id'], branding['name'])
        for branding in email_branding
    ]


def convert_dictionary_to_wtforms_choices_format(dictionary, value, label):
    return [
        (item[value], item[label]) for item in dictionary
    ]


def check_contact_details_type(contact_details):
    if contact_details.startswith('http'):
        return 'url'
    elif '@' in contact_details:
        return 'email_address'
    else:
        return 'phone_number'
