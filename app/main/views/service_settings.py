from datetime import datetime

import pytz
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from notifications_python_client.errors import HTTPError

from app import (
    billing_api_client,
    current_service,
    email_branding_client,
    inbound_number_client,
    organisations_client,
    service_api_client,
    user_api_client,
    zendesk_client,
)
from app.main import main
from app.main.forms import (
    BrandingOptionsEmail,
    ConfirmPasswordForm,
    FreeSMSAllowance,
    InternationalSMSForm,
    LetterBranding,
    LinkOrganisationsForm,
    OrganisationTypeForm,
    RenameServiceForm,
    RequestToGoLiveForm,
    SearchTemplatesForm,
    ServiceContactDetailsForm,
    ServiceDataRetentionEditForm,
    ServiceDataRetentionForm,
    ServiceEditInboundNumberForm,
    ServiceInboundNumberForm,
    ServiceLetterContactBlockForm,
    ServicePostageForm,
    ServicePreviewBranding,
    ServiceReplyToEmailForm,
    ServiceSetBranding,
    ServiceSmsSenderForm,
    ServiceSwitchLettersForm,
    SMSPrefixForm,
    branding_options_dict,
)
from app.utils import (
    AgreementInfo,
    email_safe,
    get_cdn_domain,
    user_has_permissions,
    user_is_platform_admin,
)


@main.route("/services/<service_id>/service-settings")
@login_required
@user_has_permissions('manage_service', 'manage_api_keys')
def service_settings(service_id):
    return render_template('views/service-settings.html')


@main.route("/services/<service_id>/service-settings/name", methods=['GET', 'POST'])
@login_required
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


@main.route("/services/<service_id>/service-settings/name/confirm", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def service_name_change_confirm(service_id):
    # Validate password for form
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)

    form = ConfirmPasswordForm(_check_password)

    if form.validate_on_submit():
        try:
            service_api_client.update_service(
                current_service.id,
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


@main.route("/services/<service_id>/service-settings/request-to-go-live")
@login_required
@user_has_permissions('manage_service')
def request_to_go_live(service_id):

    agreement_signed = AgreementInfo.from_current_user().agreement_signed

    return render_template(
        'views/service-settings/request-to-go-live.html',
        show_agreement=agreement_signed is not None,
        agreement_signed=agreement_signed,
    )


@main.route("/services/<service_id>/service-settings/submit-request-to-go-live", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def submit_request_to_go_live(service_id):
    form = RequestToGoLiveForm()

    if form.validate_on_submit():
        zendesk_client.create_ticket(
            subject='Request to go live - {}'.format(current_service.name),
            message=(
                'Service: {service_name}\n'
                '{service_dashboard}\n'
                '\n---'
                '\nOrganisation type: {organisation_type}'
                '\nAgreement signed: {agreement}'
                '\nChecklist completed: {checklist}'
                '\nEmails in next year: {volume_email}'
                '\nText messages in next year: {volume_sms}'
                '\nLetters in next year: {volume_letter}'
                '\nConsent to research: {research_consent}'
                '\n'
                '\n---'
                '\n'
                '{service_id}, '
                '{organisation}, '
                '{service_name}, '
                '{user_name}, '
                '{user_email}, '
                '-, '
                '{date}, '
                '{volume_sms}, '
                '{volume_email}, '
                '{volume_letter}'
            ).format(
                service_name=current_service.name,
                service_dashboard=current_service.url_for('main.service_dashboard', _external=True),
                organisation_type=str(current_service.organisation_type).title(),
                agreement=AgreementInfo.from_current_user().as_human_readable,
                checklist=current_service.go_live_checklist_completed_as_yes_no,
                volume_email=form.volume_email.data,
                volume_sms=form.volume_sms.data,
                volume_letter=form.volume_letter.data,
                research_consent=form.research_consent.data.title(),
                service_id=current_service.id,
                organisation=AgreementInfo.from_current_user().owner,
                user_name=current_user.name,
                user_email=current_user.email_address,
                date=datetime.now(tz=pytz.timezone('Europe/London')).strftime('%d/%m/%Y'),
            ),
            ticket_type=zendesk_client.TYPE_QUESTION,
            user_email=current_user.email_address,
            user_name=current_user.name,
            tags=get_request_to_go_live_tags(current_service, current_user),
        )

        flash('Thanks for your request to go live. We’ll get back to you within one working day.', 'default')
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template('views/service-settings/submit-request-to-go-live.html', form=form)


@main.route("/services/<service_id>/service-settings/switch-live")
@login_required
@user_is_platform_admin
def service_switch_live(service_id):
    service_api_client.update_service(
        current_service.id,
        # TODO This limit should be set depending on the agreement signed by
        # with Notify.
        message_limit=250000 if current_service.trial_mode else 50,
        restricted=(not current_service.trial_mode)
    )
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/research-mode")
@login_required
@user_is_platform_admin
def service_switch_research_mode(service_id):
    service_api_client.update_service_with_properties(
        service_id,
        {"research_mode": not current_service.research_mode}
    )
    return redirect(url_for('.service_settings', service_id=service_id))


def switch_service_permissions(service_id, permission, sms_sender=None):

    force_service_permission(
        service_id,
        permission,
        on=permission not in current_service.permissions,
        sms_sender=sms_sender
    )


def force_service_permission(service_id, permission, on=False, sms_sender=None):

    permissions, permission = set(current_service.permissions), {permission}

    update_service_permissions(
        service_id,
        permissions | permission if on else permissions - permission,
        sms_sender=sms_sender
    )


def update_service_permissions(service_id, permissions, sms_sender=None):

    data = {'permissions': list(permissions)}

    if sms_sender:
        data['sms_sender'] = sms_sender

    service_api_client.update_service_with_properties(service_id, data)


@main.route("/services/<service_id>/service-settings/can-send-email")
@login_required
@user_is_platform_admin
def service_switch_can_send_email(service_id):
    switch_service_permissions(service_id, 'email')
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/can-send-sms")
@login_required
@user_is_platform_admin
def service_switch_can_send_sms(service_id):
    switch_service_permissions(service_id, 'sms')
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/email-auth")
@login_required
@user_is_platform_admin
def service_switch_email_auth(service_id):
    switch_service_permissions(service_id, 'email_auth')
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/can-send-precompiled-letter")
@login_required
@user_is_platform_admin
def service_switch_can_send_precompiled_letter(service_id):
    switch_service_permissions(service_id, 'precompiled_letter')
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/can-upload-document", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def service_switch_can_upload_document(service_id):
    form = ServiceContactDetailsForm()

    # If turning the permission off, or turning it on and the service already has a contact_link,
    # don't show the form to add the link
    if current_service.has_permission('upload_document') or current_service.contact_link:
        switch_service_permissions(service_id, 'upload_document')
        return redirect(url_for('.service_settings', service_id=service_id))

    if form.validate_on_submit():
        contact_type = form.contact_details_type.data

        service_api_client.update_service(
            current_service.id,
            contact_link=form.data[contact_type]
        )
        switch_service_permissions(service_id, 'upload_document')
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template('views/service-settings/contact_link.html', form=form)


@main.route("/services/<service_id>/service-settings/can-edit-folders")
@login_required
@user_is_platform_admin
def service_switch_can_edit_folders(service_id):
    switch_service_permissions(service_id, 'edit_folders')
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/archive", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def archive_service(service_id):
    if request.method == 'POST':
        service_api_client.archive_service(service_id)
        return redirect(url_for('.service_settings', service_id=service_id))
    else:
        flash('There\'s no way to reverse this! Are you sure you want to archive this service?', 'delete')
        return service_settings(service_id)


@main.route("/services/<service_id>/service-settings/suspend", methods=["GET", "POST"])
@login_required
@user_has_permissions('manage_service')
def suspend_service(service_id):
    if request.method == 'POST':
        service_api_client.suspend_service(service_id)
        return redirect(url_for('.service_settings', service_id=service_id))
    else:
        flash("This will suspend the service and revoke all api keys. Are you sure you want to suspend this service?",
              'suspend')
        return service_settings(service_id)


@main.route("/services/<service_id>/service-settings/resume", methods=["GET", "POST"])
@login_required
@user_has_permissions('manage_service')
def resume_service(service_id):
    if request.method == 'POST':
        service_api_client.resume_service(service_id)
        return redirect(url_for('.service_settings', service_id=service_id))
    else:
        flash("This will resume the service. New api key are required for this service to use the API.", 'resume')
        return service_settings(service_id)


@main.route("/services/<service_id>/service-settings/contact-link", methods=['GET', 'POST'])
@login_required
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

        service_api_client.update_service(
            current_service.id,
            contact_link=form.data[contact_type]
        )
        return redirect(current_service.url_for('.service_settings'))

    return render_template('views/service-settings/contact_link.html', form=form)


@main.route("/services/<service_id>/service-settings/set-email", methods=['GET'])
@login_required
@user_has_permissions('manage_service')
def service_set_email(service_id):
    return render_template(
        'views/service-settings/set-email.html',
    )


@main.route("/services/<service_id>/service-settings/set-reply-to-email", methods=['GET'])
@login_required
@user_has_permissions('manage_service')
def service_set_reply_to_email(service_id):
    return redirect(url_for('.service_email_reply_to', service_id=service_id))


@main.route("/services/<service_id>/service-settings/email-reply-to", methods=['GET'])
@login_required
@user_has_permissions('manage_service', 'manage_api_keys')
def service_email_reply_to(service_id):
    return render_template('views/service-settings/email_reply_to.html')


@main.route("/services/<service_id>/service-settings/email-reply-to/add", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def service_add_email_reply_to(service_id):
    form = ServiceReplyToEmailForm()
    first_email_address = current_service.count_email_reply_to_addresses == 0
    if form.validate_on_submit():
        service_api_client.add_reply_to_email_address(
            current_service.id,
            email_address=form.email_address.data,
            is_default=first_email_address if first_email_address else form.is_default.data
        )
        return redirect(url_for('.service_email_reply_to', service_id=service_id))
    return render_template(
        'views/service-settings/email-reply-to/add.html',
        form=form,
        first_email_address=first_email_address)


@main.route(
    "/services/<service_id>/service-settings/email-reply-to/<reply_to_email_id>/edit",
    methods=['GET', 'POST'],
    endpoint="service_edit_email_reply_to"
)
@main.route(
    "/services/<service_id>/service-settings/email-reply-to/<reply_to_email_id>/delete",
    methods=['GET'],
    endpoint="service_confirm_delete_email_reply_to"
)
@login_required
@user_has_permissions('manage_service')
def service_edit_email_reply_to(service_id, reply_to_email_id):
    form = ServiceReplyToEmailForm()
    reply_to_email_address = current_service.get_email_reply_to_address(reply_to_email_id)
    if request.method == 'GET':
        form.email_address.data = reply_to_email_address['email_address']
        form.is_default.data = reply_to_email_address['is_default']
    if form.validate_on_submit():
        service_api_client.update_reply_to_email_address(
            current_service.id,
            reply_to_email_id=reply_to_email_id,
            email_address=form.email_address.data,
            is_default=True if reply_to_email_address['is_default'] else form.is_default.data
        )
        return redirect(url_for('.service_email_reply_to', service_id=service_id))
    return render_template(
        'views/service-settings/email-reply-to/edit.html',
        form=form,
        reply_to_email_address_id=reply_to_email_id,
        confirm_delete=(request.endpoint == "main.service_confirm_delete_email_reply_to"),
    )


@main.route("/services/<service_id>/service-settings/email-reply-to/<reply_to_email_id>/delete", methods=['POST'])
@login_required
@user_has_permissions('manage_service')
def service_delete_email_reply_to(service_id, reply_to_email_id):
    service_api_client.delete_reply_to_email_address(
        service_id=current_service.id,
        reply_to_email_id=reply_to_email_id,
    )
    return redirect(url_for('.service_email_reply_to', service_id=service_id))


@main.route("/services/<service_id>/service-settings/set-inbound-number", methods=['GET', 'POST'])
@login_required
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
        switch_service_permissions(current_service.id, 'inbound_sms')
        return redirect(url_for('.service_settings', service_id=service_id))
    return render_template(
        'views/service-settings/set-inbound-number.html',
        form=form,
        no_available_numbers=no_available_numbers,
    )


@main.route("/services/<service_id>/service-settings/set-sms", methods=['GET'])
@login_required
@user_has_permissions('manage_service')
def service_set_sms(service_id):
    return render_template(
        'views/service-settings/set-sms.html',
    )


@main.route("/services/<service_id>/service-settings/sms-prefix", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def service_set_sms_prefix(service_id):

    form = SMSPrefixForm(enabled=(
        'on' if current_service.prefix_sms else 'off'
    ))

    form.enabled.label.text = 'Start all text messages with ‘{}:’'.format(current_service.name)

    if form.validate_on_submit():
        service_api_client.update_service(
            current_service.id,
            prefix_sms=(form.enabled.data == 'on')
        )
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/sms-prefix.html',
        form=form
    )


@main.route("/services/<service_id>/service-settings/set-international-sms", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def service_set_international_sms(service_id):
    form = InternationalSMSForm(
        enabled='on' if current_service.has_permission('international_sms') else 'off'
    )
    if form.validate_on_submit():
        force_service_permission(
            service_id,
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


@main.route("/services/<service_id>/service-settings/set-inbound-sms", methods=['GET'])
@login_required
@user_has_permissions('manage_service')
def service_set_inbound_sms(service_id):
    return render_template(
        'views/service-settings/set-inbound-sms.html',
    )


@main.route("/services/<service_id>/service-settings/set-letters", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def service_set_letters(service_id):
    form = ServiceSwitchLettersForm(
        enabled='on' if current_service.has_permission('letter') else 'off'
    )
    if form.validate_on_submit():
        force_service_permission(
            service_id,
            'letter',
            on=(form.enabled.data == 'on'),
        )
        return redirect(
            url_for(".service_settings", service_id=service_id)
        )
    return render_template(
        'views/service-settings/set-letters.html',
        form=form,
    )


@main.route("/services/<service_id>/service-settings/set-postage", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def service_set_postage(service_id):
    form = ServicePostageForm(postage=current_service.postage)

    if form.validate_on_submit():
        service_api_client.update_service(service_id, postage=form.postage.data)
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template('views/service-settings/set-postage.html', form=form)


@main.route("/services/<service_id>/service-settings/set-auth-type", methods=['GET'])
@login_required
@user_has_permissions('manage_service')
def service_set_auth_type(service_id):
    return render_template(
        'views/service-settings/set-auth-type.html',
    )


@main.route("/services/<service_id>/service-settings/letter-contacts", methods=['GET'])
@login_required
@user_has_permissions('manage_service', 'manage_api_keys')
def service_letter_contact_details(service_id):
    letter_contact_details = service_api_client.get_letter_contacts(service_id)
    return render_template(
        'views/service-settings/letter-contact-details.html',
        letter_contact_details=letter_contact_details)


@main.route("/services/<service_id>/service-settings/letter-contact/add", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def service_add_letter_contact(service_id):
    form = ServiceLetterContactBlockForm()
    first_contact_block = current_service.count_letter_contact_details == 0
    if form.validate_on_submit():
        service_api_client.add_letter_contact(
            current_service.id,
            contact_block=form.letter_contact_block.data.replace('\r', '') or None,
            is_default=first_contact_block if first_contact_block else form.is_default.data
        )
        if request.args.get('from_template'):
            return redirect(
                url_for('.set_template_sender', service_id=service_id, template_id=request.args.get('from_template'))
            )
        return redirect(url_for('.service_letter_contact_details', service_id=service_id))
    return render_template(
        'views/service-settings/letter-contact/add.html',
        form=form,
        first_contact_block=first_contact_block,
    )


@main.route("/services/<service_id>/service-settings/letter-contact/<letter_contact_id>/edit", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def service_edit_letter_contact(service_id, letter_contact_id):
    letter_contact_block = current_service.get_letter_contact_block(letter_contact_id)
    form = ServiceLetterContactBlockForm(
        letter_contact_block=letter_contact_block['contact_block']
    )
    if request.method == 'GET':
        form.is_default.data = letter_contact_block['is_default']
    if form.validate_on_submit():
        service_api_client.update_letter_contact(
            current_service.id,
            letter_contact_id=letter_contact_id,
            contact_block=form.letter_contact_block.data.replace('\r', '') or None,
            is_default=True if letter_contact_block['is_default'] else form.is_default.data
        )
        return redirect(url_for('.service_letter_contact_details', service_id=service_id))
    return render_template(
        'views/service-settings/letter-contact/edit.html',
        form=form,
        letter_contact_id=letter_contact_block['id'])


@main.route("/services/<service_id>/service-settings/sms-sender", methods=['GET'])
@login_required
@user_has_permissions('manage_service', 'manage_api_keys')
def service_sms_senders(service_id):
    return render_template(
        'views/service-settings/sms-senders.html',
    )


@main.route("/services/<service_id>/service-settings/sms-sender/add", methods=['GET', 'POST'])
@login_required
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
    "/services/<service_id>/service-settings/sms-sender/<sms_sender_id>/edit",
    methods=['GET', 'POST'],
    endpoint="service_edit_sms_sender"
)
@main.route(
    "/services/<service_id>/service-settings/sms-sender/<sms_sender_id>/delete",
    methods=['GET'],
    endpoint="service_confirm_delete_sms_sender"
)
@login_required
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
    return render_template(
        'views/service-settings/sms-sender/edit.html',
        form=form,
        sms_sender=sms_sender,
        inbound_number=is_inbound_number,
        sms_sender_id=sms_sender_id,
        confirm_delete=(request.endpoint == "main.service_confirm_delete_sms_sender")
    )


@main.route(
    "/services/<service_id>/service-settings/sms-sender/<sms_sender_id>/delete",
    methods=['POST'],
)
@login_required
@user_has_permissions('manage_service')
def service_delete_sms_sender(service_id, sms_sender_id):
    service_api_client.delete_sms_sender(
        service_id=current_service.id,
        sms_sender_id=sms_sender_id,
    )
    return redirect(url_for('.service_sms_senders', service_id=service_id))


@main.route("/services/<service_id>/service-settings/set-letter-contact-block", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def service_set_letter_contact_block(service_id):

    if not current_service.has_permission('letter'):
        abort(403)

    form = ServiceLetterContactBlockForm(letter_contact_block=current_service.letter_contact_block)
    if form.validate_on_submit():
        service_api_client.update_service(
            current_service.id,
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


@main.route("/services/<service_id>/service-settings/set-organisation-type", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def set_organisation_type(service_id):

    form = OrganisationTypeForm(organisation_type=current_service.organisation_type)

    if form.validate_on_submit():
        free_sms_fragment_limit = current_app.config['DEFAULT_FREE_SMS_FRAGMENT_LIMITS'].get(
            form.organisation_type.data)

        service_api_client.update_service(
            service_id,
            organisation_type=form.organisation_type.data,
        )
        billing_api_client.create_or_update_free_sms_fragment_limit(service_id, free_sms_fragment_limit)

        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/set-organisation-type.html',
        form=form,
    )


@main.route("/services/<service_id>/service-settings/set-free-sms-allowance", methods=['GET', 'POST'])
@login_required
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


@main.route("/services/<service_id>/service-settings/set-email-branding", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def service_set_email_branding(service_id):
    email_branding = email_branding_client.get_all_email_branding()

    form = ServiceSetBranding(
        all_email_brandings=get_branding_as_value_and_label(email_branding),
        current_email_branding=current_service.email_branding_id,
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
        branding_dict=get_branding_as_dict(email_branding),
        search_form=SearchTemplatesForm(),
        show_search_box=(len(email_branding) > 6)
    )


@main.route("/services/<service_id>/service-settings/preview-email-branding", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def service_preview_email_branding(service_id):
    branding_style = request.args.get('branding_style', None)

    form = ServicePreviewBranding(branding_style=branding_style)

    if form.validate_on_submit():
        branding_style = None if form.branding_style.data == 'None' else form.branding_style.data
        service_api_client.update_service(
            service_id,
            email_branding=branding_style
        )
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/preview-email-branding.html',
        form=form,
        service_id=service_id,
        action=url_for('main.service_preview_email_branding', service_id=service_id),
    )


@main.route("/services/<service_id>/service-settings/set-letter-branding", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def set_letter_branding(service_id):

    form = LetterBranding(choices=email_branding_client.get_letter_email_branding().items())

    if form.validate_on_submit():
        service_api_client.update_service(
            service_id,
            dvla_organisation=form.dvla_org_id.data
        )
        return redirect(url_for('.service_settings', service_id=service_id))

    form.dvla_org_id.data = current_service.dvla_organisation

    return render_template(
        'views/service-settings/set-letter-branding.html',
        form=form,
    )


@main.route("/services/<service_id>/service-settings/request-letter-branding", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def request_letter_branding(service_id):
    return render_template(
        'views/service-settings/request-letter-branding.html',
    )


@main.route("/services/<service_id>/service-settings/link-service-to-organisation", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def link_service_to_organisation(service_id):

    organisations = organisations_client.get_organisations()
    current_organisation = organisations_client.get_service_organisation(service_id).get('id', None)

    form = LinkOrganisationsForm(
        choices=convert_dictionary_to_wtforms_choices_format(organisations, 'id', 'name'),
        organisations=current_organisation
    )

    if form.validate_on_submit():
        if form.organisations.data != current_organisation:
            organisations_client.update_service_organisation(
                service_id,
                form.organisations.data
            )
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/link-service-to-organisation.html',
        has_organisations=organisations,
        form=form,
    )


@main.route("/services/<service_id>/branding-request/email", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def branding_request(service_id):

    branding_type = 'govuk'

    if current_service.email_branding:
        branding_type = current_service.email_branding['brand_type']

    form = BrandingOptionsEmail(
        options=branding_type
    )

    if form.validate_on_submit():
        zendesk_client.create_ticket(
            subject='Email branding request - {}'.format(current_service.name),
            message=(
                'Organisation: {}\n'
                'Service: {}\n'
                '{}\n'
                '\n---'
                '\nBranding requested: {}'
            ).format(
                AgreementInfo.from_current_user().as_info_for_branding_request,
                current_service.name,
                current_service.url_for('main.service_dashboard', _external=True),
                branding_options_dict[form.options.data],
            ),
            ticket_type=zendesk_client.TYPE_QUESTION,
            user_email=current_user.email_address,
            user_name=current_user.name,
            tags=['notify_action_add_branding'],
        )

        flash((
            'Thanks for your branding request. We’ll get back to you '
            'within one working day.'
        ), 'default')
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/branding/email-options.html',
        form=form,
    )


@main.route("/services/<service_id>/data-retention", methods=['GET'])
@login_required
@user_is_platform_admin
def data_retention(service_id):
    return render_template(
        'views/service-settings/data-retention.html',
    )


@main.route("/services/<service_id>/data-retention/add", methods=['GET', 'POST'])
@login_required
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


@main.route("/services/<service_id>/data-retention/<data_retention_id>/edit", methods=['GET', 'POST'])
@login_required
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


def get_branding_as_dict(email_branding):
    return {
        branding['id']: {
            'logo': 'https://{}/{}'.format(get_cdn_domain(), branding['logo']),
            'colour': branding['colour']
        } for branding in email_branding
    }


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


def get_request_to_go_live_tags(service, user):
    return list(_get_request_to_go_live_tags(
        service,
        AgreementInfo.from_user(user).agreement_signed,
    ))


def _get_request_to_go_live_tags(service, agreement_signed):

    BASE = 'notify_request_to_go_live'

    yield BASE

    if service.go_live_checklist_completed and agreement_signed:
        yield BASE + '_complete'
        return

    for test, tag in (
        (True, ''),
        (not service.go_live_checklist_completed, '_checklist'),
        (not agreement_signed, '_mou'),
        (service.needs_to_add_email_reply_to_address, '_email_reply_to'),
        (not service.has_team_members, '_team_member'),
        (not service.has_templates, '_template_content'),
        (service.needs_to_change_sms_sender, '_sms_sender'),
    ):
        if test:
            yield BASE + '_incomplete' + tag
