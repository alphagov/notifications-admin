from itertools import chain
from collections import OrderedDict
from flask import (
    request,
    render_template,
    redirect,
    url_for,
    flash,
    abort
)

from flask_login import (
    login_required,
    current_user
)

from notifications_python_client import HTTPError
from app.main import main
from app.main.forms import (
    InviteUserForm,
    PermissionsForm
)
from app import (user_api_client, service_api_client, invite_api_client)
from app.utils import user_has_permissions


roles = {
    'send_messages': ['send_texts', 'send_emails', 'send_letters'],
    'manage_service': ['manage_users', 'manage_templates', 'manage_settings'],
    'manage_api_keys': ['manage_api_keys']
}


@main.route("/services/<service_id>/users")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def manage_users(service_id):
    return render_template(
        'views/manage-users.html',
        service_id=service_id,
        users=user_api_client.get_users_for_service(service_id=service_id),
        current_user=current_user,
        invited_users=[
            invite for invite in invite_api_client.get_invites_for_service(service_id=service_id)
            if invite.status != 'accepted'
        ]
    )


@main.route("/services/<service_id>/users/invite", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_users', admin_override=True)
def invite_user(service_id):
    service = service_api_client.get_service(service_id)['data']

    form = InviteUserForm(invalid_email_address=current_user.email_address)

    if form.validate_on_submit():
        email_address = form.email_address.data
        # view_activity is a default role to be added to all users.
        # All users will have at minimum view_activity to allow users to see notifications,
        # templates, team members but no update privileges
        permissions = ','.join(role for role in roles.keys() if request.form.get(role) == 'y').join('view_activity')
        invited_user = invite_api_client.create_invite(
            current_user.id,
            service_id,
            email_address,
            permissions
        )

        flash('Invite sent to {}'.format(invited_user.email_address), 'default_with_tick')
        return redirect(url_for('.manage_users', service_id=service_id))

    return render_template(
        'views/invite-user.html',
        service_id=service_id,
        form=form
    )


@main.route("/services/<service_id>/users/<user_id>", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_users', admin_override=True)
def edit_user_permissions(service_id, user_id):
    # TODO we should probably using the service id here in the get user
    # call as well. eg. /user/<user_id>?&service=service_id
    user = user_api_client.get_user(user_id)
    service = service_api_client.get_service(service_id)['data']
    # Need to make the email address read only, or a disabled field?
    # Do it through the template or the form class?
    form = PermissionsForm(**{
        role: user.has_permissions(permissions=permissions) for role, permissions in roles.items()
    })

    if form.validate_on_submit():
        user_api_client.set_user_permissions(
            user_id, service_id,
            permissions=set(chain.from_iterable(
                permissions for role, permissions in roles.items() if form[role].data
            )) | {'view_activity'}
        )
        return redirect(url_for('.manage_users', service_id=service_id))

    return render_template(
        'views/edit-user-permissions.html',
        user=user,
        form=form,
        service_id=service_id
    )


@main.route("/services/<service_id>/users/<user_id>/delete", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_users', admin_override=True)
def remove_user_from_service(service_id, user_id):
    user = user_api_client.get_user(user_id)
    service = service_api_client.get_service(service_id)['data']
    # Need to make the email address read only, or a disabled field?
    # Do it through the template or the form class?
    form = PermissionsForm(**{
        role: user.has_permissions(permissions=permissions) for role, permissions in roles.items()
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
        form=form,
        service_id=service_id
    )


@main.route("/services/<service_id>/cancel-invited-user/<invited_user_id>", methods=['GET'])
@user_has_permissions('manage_users', admin_override=True)
def cancel_invited_user(service_id, invited_user_id):
    invite_api_client.cancel_invited_user(service_id=service_id, invited_user_id=invited_user_id)

    return redirect(url_for('main.manage_users', service_id=service_id))
