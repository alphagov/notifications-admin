from collections import OrderedDict

from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from notifications_python_client.errors import HTTPError
from werkzeug.exceptions import abort

from app import (
    current_organisation,
    email_branding_client,
    letter_branding_client,
    org_invite_api_client,
    organisations_client,
    user_api_client,
)
from app.main import main
from app.main.forms import (
    ConfirmPasswordForm,
    CreateOrUpdateOrganisation,
    GoLiveNotesForm,
    InviteOrgUserForm,
    OrganisationAgreementSignedForm,
    OrganisationCrownStatusForm,
    OrganisationDomainsForm,
    OrganisationOrganisationTypeForm,
    PreviewBranding,
    RenameOrganisationForm,
    SearchByNameForm,
    SearchUsersForm,
    SetEmailBranding,
    SetLetterBranding,
)
from app.main.views.service_settings import get_branding_as_value_and_label
from app.utils import user_has_permissions, user_is_platform_admin


@main.route("/organisations", methods=['GET'])
@login_required
@user_is_platform_admin
def organisations():
    orgs = organisations_client.get_organisations()

    return render_template(
        'views/organisations/index.html',
        organisations=orgs,
        search_form=SearchByNameForm(),
    )


@main.route("/organisations/add", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def add_organisation():
    form = CreateOrUpdateOrganisation()

    if form.validate_on_submit():
        organisations_client.create_organisation(
            name=form.name.data,
        )

        return redirect(url_for('.organisations'))

    return render_template(
        'views/organisations/add-organisation.html',
        form=form
    )


@main.route("/organisations/<org_id>", methods=['GET'])
@login_required
@user_has_permissions()
def organisation_dashboard(org_id):
    organisation_services = [
        service for service in organisations_client.get_organisation_services(org_id)
        if service['active'] and not service['restricted']
    ]
    for service in organisation_services:
        has_permission = current_user.has_permission_for_service(service['id'], 'view_activity')
        service.update({'has_permission_to_view': has_permission})

    return render_template(
        'views/organisations/organisation/index.html',
        organisation_services=organisation_services
    )


@main.route("/organisations/<org_id>/trial-services", methods=['GET'])
@login_required
@user_is_platform_admin
def organisation_trial_mode_services(org_id):
    organisation_services = organisations_client.get_organisation_services(org_id)

    return render_template(
        'views/organisations/organisation/trial-mode-services.html',
        search_form=SearchByNameForm(),
        services=[service for service in organisation_services if not service['active'] or service['restricted']]
    )


@main.route("/organisations/<org_id>/users", methods=['GET'])
@login_required
@user_has_permissions()
def manage_org_users(org_id):
    users = sorted(
        user_api_client.get_users_for_organisation(org_id=org_id) + [
            invite for invite in org_invite_api_client.get_invites_for_organisation(org_id=org_id)
            if invite.status != 'accepted'
        ],
        key=lambda user: user.email_address,
    )

    return render_template(
        'views/organisations/organisation/users/index.html',
        users=users,
        show_search_box=(len(users) > 7),
        form=SearchUsersForm(),
    )


@main.route("/organisations/<org_id>/users/invite", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def invite_org_user(org_id):
    form = InviteOrgUserForm(
        invalid_email_address=current_user.email_address
    )
    if form.validate_on_submit():
        email_address = form.email_address.data
        invited_org_user = org_invite_api_client.create_invite(
            current_user.id,
            org_id,
            email_address
        )

        flash('Invite sent to {}'.format(invited_org_user.email_address), 'default_with_tick')
        return redirect(url_for('.manage_org_users', org_id=org_id))

    return render_template(
        'views/organisations/organisation/users/invite-org-user.html',
        form=form
    )


@main.route("/organisations/<org_id>/users/<user_id>", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def edit_user_org_permissions(org_id, user_id):
    user = user_api_client.get_user(user_id)

    return render_template(
        'views/organisations/organisation/users/user/index.html',
        user=user
    )


@main.route("/organisations/<org_id>/users/<user_id>/delete", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def remove_user_from_organisation(org_id, user_id):
    user = user_api_client.get_user(user_id)
    if request.method == 'POST':
        try:
            organisations_client.remove_user_from_organisation(org_id, user_id)
        except HTTPError as e:
            msg = "You cannot remove the only user for a service"
            if e.status_code == 400 and msg in e.message:
                flash(msg, 'info')
                return redirect(url_for(
                    '.manage_org_users',
                    org_id=org_id))
            else:
                abort(500, e)

        return redirect(url_for(
            '.manage_org_users',
            org_id=org_id
        ))

    flash('Are you sure you want to remove {}?'.format(user.name), 'remove')
    return render_template(
        'views/organisations/organisation/users/user/index.html',
        user=user,
    )


@main.route("/organisations/<org_id>/cancel-invited-user/<invited_user_id>", methods=['GET'])
@login_required
@user_has_permissions()
def cancel_invited_org_user(org_id, invited_user_id):
    org_invite_api_client.cancel_invited_user(org_id=org_id, invited_user_id=invited_user_id)

    return redirect(url_for('main.manage_org_users', org_id=org_id))


@main.route("/organisations/<org_id>/settings/", methods=['GET'])
@login_required
@user_has_permissions()
def organisation_settings(org_id):

    email_branding = 'GOV.UK'

    if current_organisation['email_branding_id']:
        email_branding = email_branding_client.get_email_branding(
            current_organisation['email_branding_id']
        )['email_branding']['name']

    letter_branding = None

    if current_organisation['letter_branding_id']:
        letter_branding = letter_branding_client.get_letter_branding(
            current_organisation['letter_branding_id']
        )['name']

    return render_template(
        'views/organisations/organisation/settings/index.html',
        email_branding=email_branding,
        letter_branding=letter_branding,
    )


@main.route("/organisations/<org_id>/settings/edit-name", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def edit_organisation_name(org_id):
    form = RenameOrganisationForm()

    if request.method == 'GET':
        form.name.data = current_organisation.get('name')

    if form.validate_on_submit():
        unique_name = organisations_client.is_organisation_name_unique(org_id, form.name.data)
        if not unique_name:
            form.name.errors.append("This organisation name is already in use")
            return render_template('views/organisations/organisation/settings/edit-name/index.html', form=form)
        session['organisation_name_change'] = form.name.data
        return redirect(url_for('.confirm_edit_organisation_name', org_id=org_id))

    return render_template(
        'views/organisations/organisation/settings/edit-name/index.html',
        form=form,
    )


@main.route("/organisations/<org_id>/settings/edit-type", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
@user_is_platform_admin
def edit_organisation_type(org_id):

    form = OrganisationOrganisationTypeForm(
        organisation_type=current_organisation['organisation_type']
    )

    if form.validate_on_submit():
        organisations_client.update_organisation(
            current_organisation['id'],
            organisation_type=form.organisation_type.data,
        )
        return redirect(url_for('.organisation_settings', org_id=org_id))

    return render_template(
        'views/organisations/organisation/settings/edit-type.html',
        form=form,
    )


@main.route("/organisations/<org_id>/settings/edit-crown-status", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
@user_is_platform_admin
def edit_organisation_crown_status(org_id):

    form = OrganisationCrownStatusForm(
        crown_status={
            True: 'crown',
            False: 'non-crown',
            None: 'unknown',
        }.get(current_organisation['crown'])
    )

    if form.validate_on_submit():
        organisations_client.update_organisation(
            current_organisation['id'],
            crown={
                'crown': True,
                'non-crown': False,
                'unknown': None,
            }.get(form.crown_status.data),
        )
        return redirect(url_for('.organisation_settings', org_id=org_id))

    return render_template(
        'views/organisations/organisation/settings/edit-crown-status.html',
        form=form,
    )


@main.route("/organisations/<org_id>/settings/edit-agreement", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
@user_is_platform_admin
def edit_organisation_agreement(org_id):

    form = OrganisationAgreementSignedForm(
        agreement_signed={
            True: 'yes',
            False: 'no',
            None: 'unknown',
        }.get(current_organisation['agreement_signed'])
    )

    if form.validate_on_submit():
        organisations_client.update_organisation(
            current_organisation['id'],
            agreement_signed={
                'yes': True,
                'no': False,
                'unknown': None,
            }.get(form.agreement_signed.data),
        )
        return redirect(url_for('.organisation_settings', org_id=org_id))

    return render_template(
        'views/organisations/organisation/settings/edit-agreement.html',
        form=form,
    )


@main.route("/organisations/<org_id>/settings/set-email-branding", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
@user_is_platform_admin
def edit_organisation_email_branding(org_id):

    email_branding = email_branding_client.get_all_email_branding()

    form = SetEmailBranding(
        all_branding_options=get_branding_as_value_and_label(email_branding),
        current_branding=current_organisation['email_branding_id'],
    )

    if form.validate_on_submit():
        return redirect(url_for(
            '.organisation_preview_email_branding',
            org_id=org_id,
            branding_style=form.branding_style.data,
        ))

    return render_template(
        'views/organisations/organisation/settings/set-email-branding.html',
        form=form,
        search_form=SearchByNameForm()
    )


@main.route("/organisations/<org_id>/settings/preview-email-branding", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
@user_is_platform_admin
def organisation_preview_email_branding(org_id):

    branding_style = request.args.get('branding_style', None)

    form = PreviewBranding(branding_style=branding_style)

    if form.validate_on_submit():
        organisations_client.update_organisation(
            org_id,
            email_branding_id=form.branding_style.data
        )
        return redirect(url_for('.organisation_settings', org_id=org_id))

    return render_template(
        'views/organisations/organisation/settings/preview-email-branding.html',
        form=form,
        action=url_for('main.organisation_preview_email_branding', org_id=org_id),
    )


@main.route("/organisations/<org_id>/settings/set-letter-branding", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def edit_organisation_letter_branding(org_id):
    letter_branding = letter_branding_client.get_all_letter_branding()

    form = SetLetterBranding(
        all_branding_options=get_branding_as_value_and_label(letter_branding),
        current_branding=current_organisation['letter_branding_id'],
    )

    if form.validate_on_submit():
        return redirect(url_for(
            '.organisation_preview_letter_branding',
            org_id=org_id,
            branding_style=form.branding_style.data,
        ))

    return render_template(
        'views/organisations/organisation/settings/set-letter-branding.html',
        form=form,
        search_form=SearchByNameForm()
    )


@main.route("/organisations/<org_id>/settings/preview-letter-branding", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def organisation_preview_letter_branding(org_id):
    branding_style = request.args.get('branding_style')

    form = PreviewBranding(branding_style=branding_style)

    if form.validate_on_submit():
        organisations_client.update_organisation(
            org_id,
            letter_branding_id=form.branding_style.data
        )
        return redirect(url_for('.organisation_settings', org_id=org_id))

    return render_template(
        'views/organisations/organisation/settings/preview-letter-branding.html',
        form=form,
        action=url_for('main.organisation_preview_letter_branding', org_id=org_id),
    )


@main.route("/organisations/<org_id>/settings/edit-organisation-domains", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
@user_is_platform_admin
def edit_organisation_domains(org_id):

    form = OrganisationDomainsForm()

    if form.validate_on_submit():
        organisations_client.update_organisation(
            org_id,
            domains=list(OrderedDict.fromkeys(
                domain.lower()
                for domain in filter(None, form.domains.data)
            )),
        )
        return redirect(url_for('.organisation_settings', org_id=org_id))

    form.populate(current_organisation.get('domains', []))

    return render_template(
        'views/organisations/organisation/settings/edit-domains.html',
        form=form,
    )


@main.route("/organisations/<org_id>/settings/edit-name/confirm", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def confirm_edit_organisation_name(org_id):
    # Validate password for form
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)

    form = ConfirmPasswordForm(_check_password)

    if form.validate_on_submit():
        try:
            organisations_client.update_organisation_name(
                current_organisation['id'],
                name=session['organisation_name_change'],
            )
        except HTTPError as e:
            error_msg = "Organisation name already exists"
            if e.status_code == 400 and error_msg in e.message:
                # Redirect the user back to the change service name screen
                flash('This organisation name is already in use', 'error')
                return redirect(url_for('main.edit_organisation_name', org_id=org_id))
            else:
                raise e
        else:
            session.pop('organisation_name_change')
            return redirect(url_for('.organisation_settings', org_id=org_id))
    return render_template(
        'views/organisations/organisation/settings/edit-name/confirm.html',
        new_name=session['organisation_name_change'],
        form=form)


@main.route("/organisations/<org_id>/settings/edit-go-live-notes", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
@user_is_platform_admin
def edit_organisation_go_live_notes(org_id):

    form = GoLiveNotesForm()

    if form.validate_on_submit():
        organisations_client.update_organisation(
            org_id,
            request_to_go_live_notes=form.request_to_go_live_notes.data
        )
        return redirect(url_for('.organisation_settings', org_id=org_id))

    org = organisations_client.get_organisation(org_id)
    form.request_to_go_live_notes.data = org['request_to_go_live_notes']

    return render_template(
        'views/organisations/organisation/settings/edit-go-live-notes.html',
        form=form,
    )
