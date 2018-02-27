from flask import (
    redirect,
    render_template,
    url_for,
    flash,
    request
)
from flask_login import (
    login_required,
    current_user
)

from app import (
    organisations_client,
    org_invite_api_client,
    user_api_client,
)
from app.main.forms import (
    SearchUsersForm,
    InviteOrgUserForm,
)
from app.main import main
from app.main.forms import CreateOrUpdateOrganisation
from app.utils import user_has_permissions

from notifications_python_client.errors import HTTPError
from werkzeug.exceptions import abort


@main.route("/organisations", methods=['GET'])
@login_required
@user_has_permissions(admin_override=True)
def organisations():
    orgs = organisations_client.get_organisations()

    return render_template(
        'views/organisations/index.html',
        organisations=orgs
    )


@main.route("/organisations/add", methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
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
@user_has_permissions(admin_override=True)
def organisation_dashboard(org_id):
    organisation_services = organisations_client.get_organisation_services(org_id)

    return render_template(
        'views/organisations/organisation/index.html',
        organisation_services=organisation_services
    )


@main.route("/organisations/<org_id>/edit", methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
def update_organisation(org_id):
    org = organisations_client.get_organisation(org_id)

    form = CreateOrUpdateOrganisation()

    if form.validate_on_submit():
        organisations_client.update_organisation(
            org_id=org_id,
            name=form.name.data
        )

        return redirect(url_for('.organisations'))

    form.name.data = org['name']

    return render_template(
        'views/organisations/organisation/update-organisation.html',
        form=form,
        organisation=org
    )


@main.route("/organisations/<org_id>/users", methods=['GET'])
@login_required
@user_has_permissions(admin_override=True)
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
@user_has_permissions(admin_override=True)
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
@user_has_permissions(admin_override=True)
def edit_user_org_permissions(org_id, user_id):
    user = user_api_client.get_user(user_id)

    return render_template(
        'views/organisations/organisation/users/user/index.html',
        user=user
    )


@main.route("/organisations/<org_id>/users/<user_id>/delete", methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
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
@user_has_permissions(admin_override=True)
def cancel_invited_org_user(org_id, invited_user_id):
    org_invite_api_client.cancel_invited_user(org_id=org_id, invited_user_id=invited_user_id)

    return redirect(url_for('main.manage_org_users', org_id=org_id))
