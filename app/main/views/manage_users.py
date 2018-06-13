from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from notifications_python_client.errors import HTTPError

from app import (
    current_service,
    invite_api_client,
    service_api_client,
    user_api_client,
)
from app.main import main
from app.main.forms import (
    AdminInviteUserForm,
    AdminPermissionsForm,
    SearchUsersForm,
)
from app.notify_client.models import roles
from app.utils import user_has_permissions


@main.route("/services/<service_id>/users")
@login_required
@user_has_permissions('view_activity')
def manage_users(service_id):
    users = sorted(
        user_api_client.get_users_for_service(service_id=service_id) + [
            invite for invite in invite_api_client.get_invites_for_service(service_id=service_id)
            if invite.status != 'accepted'
        ],
        key=lambda user: user.email_address,
    )

    return render_template(
        'views/manage-users.html',
        users=users,
        current_user=current_user,
        show_search_box=(len(users) > 7),
        form=SearchUsersForm(),
    )


@main.route("/services/<service_id>/users/invite", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def invite_user(service_id):

    form = AdminInviteUserForm(
        invalid_email_address=current_user.email_address
    )

    service_has_email_auth = 'email_auth' in current_service['permissions']
    if not service_has_email_auth:
        form.login_authentication.data = 'sms_auth'

    if form.validate_on_submit():
        email_address = form.email_address.data
        invited_user = invite_api_client.create_invite(
            current_user.id,
            service_id,
            email_address,
            form.permissions,
            form.login_authentication.data
        )

        flash('Invite sent to {}'.format(invited_user.email_address), 'default_with_tick')
        return redirect(url_for('.manage_users', service_id=service_id))

    return render_template(
        'views/invite-user.html',
        form=form,
        service_has_email_auth=service_has_email_auth
    )


@main.route("/services/<service_id>/users/<user_id>", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def edit_user_permissions(service_id, user_id):
    service_has_email_auth = 'email_auth' in current_service['permissions']
    # TODO we should probably using the service id here in the get user
    # call as well. eg. /user/<user_id>?&service=service_id
    user = user_api_client.get_user(user_id)
    user_has_no_mobile_number = user.mobile_number is None

    form = AdminPermissionsForm(
        **{role: user.has_permission_for_service(service_id, role) for role in roles.keys()},
        login_authentication=user.auth_type
    )
    if form.validate_on_submit():
        user_api_client.set_user_permissions(
            user_id, service_id,
            permissions=form.permissions,
        )
        if service_has_email_auth:
            user_api_client.update_user_attribute(user_id, auth_type=form.login_authentication.data)
        return redirect(url_for('.manage_users', service_id=service_id))

    return render_template(
        'views/edit-user-permissions.html',
        user=user,
        form=form,
        service_has_email_auth=service_has_email_auth,
        user_has_no_mobile_number=user_has_no_mobile_number
    )


@main.route("/services/<service_id>/users/<user_id>/delete", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_service')
def remove_user_from_service(service_id, user_id):
    user = user_api_client.get_user(user_id)
    # Need to make the email address read only, or a disabled field?
    # Do it through the template or the form class?
    form = AdminPermissionsForm(**{
        role: user.has_permission_for_service(service_id, role) for role in roles.keys()
    })

    if request.method == 'POST':
        try:
            service_api_client.remove_user_from_service(service_id, user_id)
        except HTTPError as e:
            msg = "You cannot remove the only user for a service"
            if e.status_code == 400 and msg in e.message:
                flash(msg, 'info')
                return redirect(url_for(
                    '.manage_users',
                    service_id=service_id))
            else:
                abort(500, e)

        return redirect(url_for(
            '.manage_users',
            service_id=service_id
        ))

    flash('Are you sure you want to remove {}?'.format(user.name), 'remove')
    return render_template(
        'views/edit-user-permissions.html',
        user=user,
        form=form
    )


@main.route("/services/<service_id>/cancel-invited-user/<invited_user_id>", methods=['GET'])
@user_has_permissions('manage_service')
def cancel_invited_user(service_id, invited_user_id):
    invite_api_client.cancel_invited_user(service_id=service_id, invited_user_id=invited_user_id)

    return redirect(url_for('main.manage_users', service_id=service_id))
