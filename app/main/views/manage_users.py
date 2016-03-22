from flask import (
    request,
    render_template,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_required,
    current_user
)

from app.main import main
from app.main.forms import (
    InviteUserForm,
    PermisisonsForm
)
from app.main.dao.services_dao import get_service_by_id
from app import user_api_client
from app import invite_api_client
from app.utils import user_has_permissions


@main.route("/services/<service_id>/users")
@login_required
def manage_users(service_id):
    users = user_api_client.get_users_for_service(service_id=service_id)
    invited_users = invite_api_client.get_invites_for_service(service_id=service_id)
    filtered_invites = []
    for invite in invited_users:
        if invite.status != 'accepted':
            filtered_invites.append(invite)
    return render_template('views/manage-users.html',
                           service_id=service_id,
                           users=users,
                           current_user=current_user,
                           invited_users=filtered_invites)


@main.route("/services/<service_id>/users/invite", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_users', admin_override=True)
def invite_user(service_id):
    service = get_service_by_id(service_id)

    form = InviteUserForm(current_user.email_address)
    if form.validate_on_submit():
        email_address = form.email_address.data
        permissions = _get_permissions(request.form)
        invited_user = invite_api_client.create_invite(current_user.id, service_id, email_address, permissions)

        flash('Invite sent to {}'.format(invited_user.email_address), 'default_with_tick')
        return redirect(url_for('.manage_users', service_id=service_id))

    return render_template(
        'views/invite-user.html',
        user=None,
        service_id=service_id,
        form=form
    )


@main.route("/services/<service_id>/users/<user_id>", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_users', admin_override=True)
def edit_user_permissions(service_id, user_id):
    # TODO we should probably using the service id here in the get user
    # call as well. eg. /user/<user_id>?&service_id=service_id
    user = user_api_client.get_user(user_id)
    service = get_service_by_id(service_id)
    # Need to make the email address read only, or a disabled field?
    # Do it through the template or the form class?
    form = PermisisonsForm(**{
        'send_messages': 'yes' if user.has_permissions(
            permissions=['send_texts', 'send_emails', 'send_letters']) else 'no',
        'manage_service': 'yes' if user.has_permissions(
            permissions=['manage_users', 'manage_templates', 'manage_settings']) else 'no',
        'manage_api_keys': 'yes' if user.has_permissions(
            permissions=['manage_api_keys', 'access_developer_docs']) else 'no'
        })

    if form.validate_on_submit():
        permissions = []
        permissions.extend(
            _convert_role_to_permissions('send_messages') if form.send_messages.data == 'yes' else [])
        permissions.extend(
            _convert_role_to_permissions('manage_service') if form.manage_service.data == 'yes' else [])
        permissions.extend(
            _convert_role_to_permissions('manage_api_keys') if form.manage_api_keys.data == 'yes' else [])
        user_api_client.set_user_permissions(user_id, service_id, permissions)
        return redirect(url_for('.manage_users', service_id=service_id))

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


def _convert_role_to_permissions(role):
    if role == 'send_messages':
        return ['send_texts', 'send_emails', 'send_letters']
    elif role == 'manage_service':
        return ['manage_users', 'manage_templates', 'manage_settings']
    elif role == 'manage_api_keys':
        return ['manage_api_keys', 'access_developer_docs']
    return []


# TODO replace with method which converts each 'role' into the list
# of permissions like the method above :)
def _get_permissions(form):
    permissions = []
    if form.get('send_messages') and form['send_messages'] == 'yes':
        permissions.append('send_messages')
    if form.get('manage_service') and form['manage_service'] == 'yes':
        permissions.append('manage_service')
    if form.get('manage_api_keys') and form['manage_api_keys'] == 'yes':
        permissions.append('manage_api_keys')
    return ','.join(permissions)
