import requests
from flask import (
    render_template,
    redirect,
    request,
    url_for,
    session,
    flash,
    abort,
    current_app
)

from flask_login import (
    login_required,
    current_user
)

from notifications_utils.field import Field
from notifications_python_client.errors import HTTPError

from app import service_api_client
from app.main import main
from app.utils import user_has_permissions, email_safe, get_cdn_domain
from app.main.forms import (
    ConfirmPasswordForm,
    RenameServiceForm,
    RequestToGoLiveForm,
    ServiceReplyToEmailForm,
    ServiceInboundNumberForm,
    ServiceSmsSenderForm,
    ServiceLetterContactBlockForm,
    ServiceBrandingOrg,
    LetterBranding,
    InternationalSMSForm,
    OrganisationTypeForm,
    FreeSMSAllowance,
    ServiceEditInboundNumberForm,
    SMSPrefixForm,
)
from app import user_api_client, current_service, organisations_client, inbound_number_client, billing_api_client
from notifications_utils.formatters import formatted_list


@main.route("/services/<service_id>/service-settings")
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_settings(service_id):
    letter_branding_organisations = organisations_client.get_letter_organisations()
    if current_service['organisation']:
        organisation = organisations_client.get_organisation(current_service['organisation'])['organisation']
    else:
        organisation = None

    inbound_number = inbound_number_client.get_inbound_sms_number_for_service(service_id)
    disp_inbound_number = inbound_number['data'].get('number', '')
    reply_to_email_addresses = service_api_client.get_reply_to_email_addresses(service_id)
    reply_to_email_address_count = len(reply_to_email_addresses)
    default_reply_to_email_address = next(
        (x['email_address'] for x in reply_to_email_addresses if x['is_default']), "Not set"
    )
    letter_contact_details = service_api_client.get_letter_contacts(service_id)
    letter_contact_details_count = len(letter_contact_details)
    default_letter_contact_block = next(
        (Field(x['contact_block'], html='escape') for x in letter_contact_details if x['is_default']), "Not set"
    )
    sms_senders = service_api_client.get_sms_senders(service_id)
    sms_sender_count = len(sms_senders)
    default_sms_sender = next(
        (Field(x['sms_sender'], html='escape') for x in sms_senders if x['is_default']), "None"
    )

    free_sms_fragment_limit = billing_api_client.get_free_sms_fragment_limit_for_year(service_id)

    return render_template(
        'views/service-settings.html',
        organisation=organisation,
        letter_branding=letter_branding_organisations.get(
            current_service.get('dvla_organisation', '001')
        ),
        can_receive_inbound=('inbound_sms' in current_service['permissions']),
        inbound_number=disp_inbound_number,
        default_reply_to_email_address=default_reply_to_email_address,
        reply_to_email_address_count=reply_to_email_address_count,
        default_letter_contact_block=default_letter_contact_block,
        letter_contact_details_count=letter_contact_details_count,
        default_sms_sender=default_sms_sender,
        sms_sender_count=sms_sender_count,
        free_sms_fragment_limit=free_sms_fragment_limit,
        prefix_sms=current_service['prefix_sms'],
    )


@main.route("/services/<service_id>/service-settings/name", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_name_change(service_id):
    form = RenameServiceForm()

    if request.method == 'GET':
        form.name.data = current_service.get('name')

    if form.validate_on_submit():
        unique_name = service_api_client.is_service_name_unique(form.name.data, email_safe(form.name.data))
        if not unique_name:
            form.name.errors.append("This service name is already in use")
            return render_template('views/service-settings/name.html', form=form)
        session['service_name_change'] = form.name.data
        return redirect(url_for('.service_name_change_confirm', service_id=service_id))

    return render_template(
        'views/service-settings/name.html',
        form=form)


@main.route("/services/<service_id>/service-settings/name/confirm", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_name_change_confirm(service_id):
    # Validate password for form
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)

    form = ConfirmPasswordForm(_check_password)

    if form.validate_on_submit():
        try:
            service_api_client.update_service(
                current_service['id'],
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


@main.route("/services/<service_id>/service-settings/request-to-go-live", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_request_to_go_live(service_id):
    form = RequestToGoLiveForm()

    if form.validate_on_submit():

        data = {
            'person_email': current_user.email_address,
            'person_name': current_user.name,
            'department_id': current_app.config.get('DESKPRO_DEPT_ID'),
            'agent_team_id': current_app.config.get('DESKPRO_ASSIGNED_AGENT_TEAM_ID'),
            'subject': 'Request to go live - {}'.format(current_service['name']),
            'message': (
                'On behalf of {} ({})\n\nExpected usage\n---'
                '\nMOU in place: {}'
                '\nChannel: {}\nStart date: {}\nStart volume: {}'
                '\nPeak volume: {}\nUpload or API: {}'
            ).format(
                current_service['name'],
                url_for('main.service_dashboard', service_id=current_service['id'], _external=True),
                form.mou.data,
                formatted_list(filter(None, (
                    'email' if form.channel_email.data else None,
                    'text messages' if form.channel_sms.data else None,
                    'letters' if form.channel_letter.data else None,
                )), before_each='', after_each=''),
                form.start_date.data,
                form.start_volume.data,
                form.peak_volume.data,
                form.upload_or_api.data

            )
        }
        headers = {
            "X-DeskPRO-API-Key": current_app.config.get('DESKPRO_API_KEY'),
            'Content-Type': "application/x-www-form-urlencoded"
        }
        resp = requests.post(
            current_app.config.get('DESKPRO_API_HOST') + '/api/tickets',
            data=data,
            headers=headers
        )
        if resp.status_code != 201:
            current_app.logger.error(
                "Deskpro create ticket request failed with {} '{}'".format(
                    resp.status_code,
                    resp.json())
            )
            abort(500, "Request to go live submission failed")

        flash('We’ve received your request to go live', 'default')
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template('views/service-settings/request-to-go-live.html', form=form)


@main.route("/services/<service_id>/service-settings/switch-live")
@login_required
@user_has_permissions(admin_override=True)
def service_switch_live(service_id):
    service_api_client.update_service(
        current_service['id'],
        # TODO This limit should be set depending on the agreement signed by
        # with Notify.
        message_limit=250000 if current_service['restricted'] else 50,
        restricted=(not current_service['restricted'])
    )
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/research-mode")
@login_required
@user_has_permissions(admin_override=True)
def service_switch_research_mode(service_id):
    service_api_client.update_service_with_properties(
        service_id,
        {"research_mode": not current_service['research_mode']}
    )
    return redirect(url_for('.service_settings', service_id=service_id))


def switch_service_permissions(service_id, permission, sms_sender=None):

    force_service_permission(
        service_id,
        permission,
        on=permission not in current_service['permissions'],
        sms_sender=sms_sender
    )


def force_service_permission(service_id, permission, on=False, sms_sender=None):

    permissions, permission = set(current_service['permissions']), {permission}

    update_service_permissions(
        service_id,
        permissions | permission if on else permissions - permission,
        sms_sender=sms_sender
    )


def update_service_permissions(service_id, permissions, sms_sender=None):

    current_service['permissions'] = list(permissions)

    data = {'permissions': current_service['permissions']}

    if sms_sender:
        data['sms_sender'] = sms_sender

    service_api_client.update_service_with_properties(service_id, data)


@main.route("/services/<service_id>/service-settings/can-send-letters")
@login_required
@user_has_permissions(admin_override=True)
def service_switch_can_send_letters(service_id):
    switch_service_permissions(service_id, 'letter')
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/send-letters-as-pdf")
@login_required
@user_has_permissions(admin_override=True)
def service_switch_send_letters_as_pdf(service_id):
    switch_service_permissions(service_id, 'letters_as_pdf')
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/can-send-international-sms")
@login_required
@user_has_permissions(admin_override=True)
def service_switch_can_send_international_sms(service_id):
    switch_service_permissions(service_id, 'international_sms')
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/can-send-email")
@login_required
@user_has_permissions(admin_override=True)
def service_switch_can_send_email(service_id):
    switch_service_permissions(service_id, 'email')
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/can-send-sms")
@login_required
@user_has_permissions(admin_override=True)
def service_switch_can_send_sms(service_id):
    switch_service_permissions(service_id, 'sms')
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/email-auth")
@login_required
@user_has_permissions(admin_override=True)
def service_switch_email_auth(service_id):
    switch_service_permissions(service_id, 'email_auth')
    return redirect(url_for('.service_settings', service_id=service_id))


@main.route("/services/<service_id>/service-settings/archive", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def archive_service(service_id):
    if request.method == 'POST':
        service_api_client.archive_service(service_id)
        return redirect(url_for('.service_settings', service_id=service_id))
    else:
        flash('There\'s no way to reverse this! Are you sure you want to archive this service?', 'delete')
        return service_settings(service_id)


@main.route("/services/<service_id>/service-settings/suspend", methods=["GET", "POST"])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
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
@user_has_permissions('manage_settings', admin_override=True)
def resume_service(service_id):
    if request.method == 'POST':
        service_api_client.resume_service(service_id)
        return redirect(url_for('.service_settings', service_id=service_id))
    else:
        flash("This will resume the service. New api key are required for this service to use the API.", 'resume')
        return service_settings(service_id)


@main.route("/services/<service_id>/service-settings/set-email", methods=['GET'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_set_email(service_id):
    return render_template(
        'views/service-settings/set-email.html',
    )


@main.route("/services/<service_id>/service-settings/set-reply-to-email", methods=['GET'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_set_reply_to_email(service_id):
    return redirect(url_for('.service_email_reply_to', service_id=service_id))


@main.route("/services/<service_id>/service-settings/email-reply-to", methods=['GET'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_email_reply_to(service_id):
    reply_to_email_addresses = service_api_client.get_reply_to_email_addresses(service_id)
    return render_template(
        'views/service-settings/email_reply_to.html',
        reply_to_email_addresses=reply_to_email_addresses)


@main.route("/services/<service_id>/service-settings/email-reply-to/add", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_add_email_reply_to(service_id):
    form = ServiceReplyToEmailForm()
    reply_to_email_address_count = len(service_api_client.get_reply_to_email_addresses(service_id))
    first_email_address = reply_to_email_address_count == 0
    if form.validate_on_submit():
        service_api_client.add_reply_to_email_address(
            current_service['id'],
            email_address=form.email_address.data,
            is_default=first_email_address if first_email_address else form.is_default.data
        )
        return redirect(url_for('.service_email_reply_to', service_id=service_id))
    return render_template(
        'views/service-settings/email-reply-to/add.html',
        form=form,
        first_email_address=first_email_address)


@main.route("/services/<service_id>/service-settings/email-reply-to/<reply_to_email_id>/edit", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_edit_email_reply_to(service_id, reply_to_email_id):
    form = ServiceReplyToEmailForm()
    reply_to_email_address = service_api_client.get_reply_to_email_address(service_id, reply_to_email_id)
    if request.method == 'GET':
        form.email_address.data = reply_to_email_address['email_address']
        form.is_default.data = reply_to_email_address['is_default']
    if form.validate_on_submit():
        service_api_client.update_reply_to_email_address(
            current_service['id'],
            reply_to_email_id=reply_to_email_id,
            email_address=form.email_address.data,
            is_default=True if reply_to_email_address['is_default'] else form.is_default.data
        )
        return redirect(url_for('.service_email_reply_to', service_id=service_id))
    return render_template(
        'views/service-settings/email-reply-to/edit.html',
        form=form,
        reply_to_email_address_id=reply_to_email_address['id'])


@main.route("/services/<service_id>/service-settings/set-inbound-number", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_set_inbound_number(service_id):
    available_inbound_numbers = inbound_number_client.get_available_inbound_sms_numbers()
    service_has_inbound_number = inbound_number_client.get_inbound_sms_number_for_service(service_id)['data'] != {}
    inbound_numbers_value_and_label = [
        (number['id'], number['number']) for number in available_inbound_numbers['data']
    ]
    no_available_numbers = available_inbound_numbers['data'] == []
    form = ServiceInboundNumberForm(
        inbound_number_choices=inbound_numbers_value_and_label
    )
    if form.validate_on_submit():
        service_api_client.add_sms_sender(
            current_service['id'],
            sms_sender=form.inbound_number.data,
            is_default=True,
            inbound_number_id=form.inbound_number.data
        )
        switch_service_permissions(current_service['id'], 'inbound_sms')
        return redirect(url_for('.service_settings', service_id=service_id))
    return render_template(
        'views/service-settings/set-inbound-number.html',
        form=form,
        no_available_numbers=no_available_numbers,
        service_has_inbound_number=service_has_inbound_number
    )


@main.route("/services/<service_id>/service-settings/set-sms", methods=['GET'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_set_sms(service_id):
    return render_template(
        'views/service-settings/set-sms.html',
    )


@main.route("/services/<service_id>/service-settings/sms-prefix", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_set_sms_prefix(service_id):

    form = SMSPrefixForm(enabled=(
        'on' if current_service['prefix_sms'] else 'off'
    ))

    form.enabled.label.text = 'Start all text messages with ‘{}:’'.format(current_service['name'])

    if form.validate_on_submit():
        service_api_client.update_service(
            current_service['id'],
            prefix_sms=(form.enabled.data == 'on')
        )
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/sms-prefix.html',
        form=form
    )


@main.route("/services/<service_id>/service-settings/set-international-sms", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_set_international_sms(service_id):
    form = InternationalSMSForm(
        enabled='on' if 'international_sms' in current_service['permissions'] else 'off'
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
@user_has_permissions('manage_settings', admin_override=True)
def service_set_inbound_sms(service_id):
    number = inbound_number_client.get_inbound_sms_number_for_service(service_id)['data'].get('number', '')
    return render_template(
        'views/service-settings/set-inbound-sms.html',
        inbound_number=number,
    )


@main.route("/services/<service_id>/service-settings/set-letters", methods=['GET'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_set_letters(service_id):
    return render_template(
        'views/service-settings/set-letters.html',
    )


@main.route("/services/<service_id>/service-settings/set-auth-type", methods=['GET'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_set_auth_type(service_id):
    return render_template(
        'views/service-settings/set-auth-type.html',
    )


@main.route("/services/<service_id>/service-settings/letter-contacts", methods=['GET'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_letter_contact_details(service_id):
    letter_contact_details = service_api_client.get_letter_contacts(service_id)
    return render_template(
        'views/service-settings/letter-contact-details.html',
        letter_contact_details=letter_contact_details)


@main.route("/services/<service_id>/service-settings/letter-contact/add", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_add_letter_contact(service_id):
    form = ServiceLetterContactBlockForm()
    letter_contact_blocks_count = len(service_api_client.get_letter_contacts(service_id))
    first_contact_block = letter_contact_blocks_count == 0
    if form.validate_on_submit():
        service_api_client.add_letter_contact(
            current_service['id'],
            contact_block=form.letter_contact_block.data.replace('\r', '') or None,
            is_default=first_contact_block if first_contact_block else form.is_default.data
        )
        return redirect(url_for('.service_letter_contact_details', service_id=service_id))
    return render_template(
        'views/service-settings/letter-contact/add.html',
        form=form,
        first_contact_block=first_contact_block)


@main.route("/services/<service_id>/service-settings/letter-contact/<letter_contact_id>/edit", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_edit_letter_contact(service_id, letter_contact_id):
    letter_contact_block = service_api_client.get_letter_contact(service_id, letter_contact_id)
    form = ServiceLetterContactBlockForm(letter_contact_block=letter_contact_block['contact_block'])
    if request.method == 'GET':
        form.is_default.data = letter_contact_block['is_default']
    if form.validate_on_submit():
        service_api_client.update_letter_contact(
            current_service['id'],
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
@user_has_permissions('manage_settings', admin_override=True)
def service_sms_senders(service_id):

    def attach_hint(sender):
        hints = []
        if sender['is_default']:
            hints += ["default"]
        if sender['inbound_number_id']:
            hints += ["receives replies"]
        if hints:
            sender['hint'] = "(" + " and ".join(hints) + ")"

    sms_senders = service_api_client.get_sms_senders(service_id)

    for sender in sms_senders:
        attach_hint(sender)

    return render_template(
        'views/service-settings/sms-senders.html',
        sms_senders=sms_senders
    )


@main.route("/services/<service_id>/service-settings/sms-sender/add", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_add_sms_sender(service_id):
    form = ServiceSmsSenderForm()
    sms_sender_count = len(service_api_client.get_sms_senders(service_id))
    first_sms_sender = sms_sender_count == 0
    if form.validate_on_submit():
        service_api_client.add_sms_sender(
            current_service['id'],
            sms_sender=form.sms_sender.data.replace('\r', '') or None,
            is_default=first_sms_sender if first_sms_sender else form.is_default.data
        )
        return redirect(url_for('.service_sms_senders', service_id=service_id))
    return render_template(
        'views/service-settings/sms-sender/add.html',
        form=form,
        first_sms_sender=first_sms_sender)


@main.route("/services/<service_id>/service-settings/sms-sender/<sms_sender_id>/edit", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_edit_sms_sender(service_id, sms_sender_id):
    sms_sender = service_api_client.get_sms_sender(service_id, sms_sender_id)
    is_inbound_number = sms_sender['inbound_number_id']
    if is_inbound_number:
        form = ServiceEditInboundNumberForm(is_default=sms_sender['is_default'])
    else:
        form = ServiceSmsSenderForm(**sms_sender)

    if form.validate_on_submit():
        service_api_client.update_sms_sender(
            current_service['id'],
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
        inbound_number=is_inbound_number
    )


@main.route("/services/<service_id>/service-settings/set-letter-contact-block", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def service_set_letter_contact_block(service_id):

    if 'letter' not in current_service['permissions']:
        abort(403)

    form = ServiceLetterContactBlockForm(letter_contact_block=current_service['letter_contact_block'])
    if form.validate_on_submit():
        service_api_client.update_service(
            current_service['id'],
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
@user_has_permissions(admin_override=True)
def set_organisation_type(service_id):

    form = OrganisationTypeForm(organisation_type=current_service.get('organisation_type'))

    if form.validate_on_submit():
        service_api_client.update_service(
            service_id,
            organisation_type=form.organisation_type.data,
        )
        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/set-organisation-type.html',
        form=form,
    )


@main.route("/services/<service_id>/service-settings/set-free-sms-allowance", methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
def set_free_sms_allowance(service_id):

    form = FreeSMSAllowance(free_sms_allowance=billing_api_client.get_free_sms_fragment_limit_for_year(service_id))

    if form.validate_on_submit():
        billing_api_client.create_or_update_free_sms_fragment_limit(service_id, form.free_sms_allowance.data)

        return redirect(url_for('.service_settings', service_id=service_id))

    return render_template(
        'views/service-settings/set-free-sms-allowance.html',
        form=form,
    )


@main.route("/services/<service_id>/service-settings/set-branding-and-org", methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
def service_set_branding_and_org(service_id):
    organisations = organisations_client.get_organisations()

    form = ServiceBrandingOrg(branding_type=current_service.get('branding'))

    # dynamically create org choices, including the null option
    form.organisation.choices = [('None', 'None')] + get_branding_as_value_and_label(organisations)

    if form.validate_on_submit():
        organisation = None if form.organisation.data == 'None' else form.organisation.data
        service_api_client.update_service(
            service_id,
            branding=form.branding_type.data,
            organisation=organisation
        )
        return redirect(url_for('.service_settings', service_id=service_id))

    form.organisation.data = current_service['organisation'] or 'None'

    return render_template(
        'views/service-settings/set-branding-and-org.html',
        form=form,
        branding_dict=get_branding_as_dict(organisations)
    )


@main.route("/services/<service_id>/service-settings/set-letter-branding", methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
def set_letter_branding(service_id):

    form = LetterBranding(choices=organisations_client.get_letter_organisations().items())

    if form.validate_on_submit():
        service_api_client.update_service(
            service_id,
            dvla_organisation=form.dvla_org_id.data
        )
        return redirect(url_for('.service_settings', service_id=service_id))

    form.dvla_org_id.data = current_service.get('dvla_organisation', '001')

    return render_template(
        'views/service-settings/set-letter-branding.html',
        form=form,
    )


def get_branding_as_value_and_label(organisations):
    return [
        (organisation['id'], organisation['name'])
        for organisation in organisations
    ]


def get_branding_as_dict(organisations):
    return {
        organisation['id']: {
            'logo': 'https://{}/{}'.format(get_cdn_domain(), organisation['logo']),
            'colour': organisation['colour']
        } for organisation in organisations
    }
