from flask import (
    request,
    render_template,
    redirect,
    abort,
    url_for,
    flash)

from flask_login import (
    login_required,
    current_user
)

from notifications_python_client.errors import HTTPError

from app.main import main
from app.main.forms import InviteUserForm
from app.main.dao.services_dao import get_service_by_id
from app import user_api_client
from app import invite_api_client
from app.utils import user_has_permissions

fake_users = [
    {
        'name': '',
        'permission_send_messages': True,
        'permission_manage_service': True,
        'permission_manage_api_keys': True,
        'active': True
    }
]


@main.route("/services/<service_id>/users")
@login_required
@user_has_permissions('manage_users', 'manage_templates', 'manage_settings')
def manage_users(service_id):
    users = user_api_client.get_users_for_service(service_id=service_id)
    invited_users = invite_api_client.get_invites_for_service(service_id=service_id)
    return render_template('views/manage-users.html',
                           service_id=service_id,
                           users=users,
                           current_user=current_user,
                           invited_users=invited_users)


@main.route("/services/<service_id>/users/invite", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_users', 'manage_templates', 'manage_settings')
def invite_user(service_id):

    service = get_service_by_id(service_id)

    form = InviteUserForm()
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
@user_has_permissions('manage_users', 'manage_templates', 'manage_settings')
def edit_user_permissions(service_id, user_id):
    # TODO we should probably using the service id here in the get user
    # call as well. eg. /user/<user_id>?&service_id=service_id
    user = user_api_client.get_user(user_id)
    service = get_service_by_id(service_id)

    form = InviteUserForm(**{
        'email_address': user.email_address,
        'send_messages': user.has_permissions(['send_texts', 'send_emails', 'send_letters']),
        'manage_service': user.has_permissions(['manage_users', 'manage_templates', 'manage_settings']),
        'manage_api_keys': user.has_permissions(['manage_api_keys', 'access_developer_docs'])
        })
    if form.validate_on_submit():
        return redirect(url_for('.manage_users', service_id=service_id))

    return render_template(
        'views/invite-user.html',
        user=user,
        form=form,
        service_id=service_id
    )


@main.route("/services/<service_id>/users/<user_id>/delete", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_users', 'manage_templates', 'manage_settings')
def delete_user(service_id, user_id):
    user = user_api_client.get_user(user_id)
    service = get_service_by_id(service_id)

    if request.method == 'POST':
        return redirect(url_for('.manage_users', service_id=service_id))

    flash(
        'Are you sure you want to delete {}’s account?'.format(user.get('name') or user['email_localpart']),
        'delete'
    )

    return render_template(
        'views/invite-user.html',
        user=user,
        service_id=service_id
    )


@main.route("/services/<service_id>/cancel-invited-user/<invited_user_id>", methods=['GET'])
@user_has_permissions('manage_users', 'manage_templates', 'manage_settings')
def cancel_invited_user(service_id, invited_user_id):
    invite_api_client.cancel_invited_user(service_id=service_id, invited_user_id=invited_user_id)

    return redirect(url_for('main.manage_users', service_id=service_id))


def _get_permissions(form):
    permissions = []
    if form.get('send_messages') and form['send_messages'] == 'yes':
        permissions.append('send_messages')
    if form.get('manage_service') and form['manage_service'] == 'yes':
        permissions.append('manage_service')
    if form.get('manage_api_keys') and form['manage_api_keys'] == 'yes':
        permissions.append('manage_api_keys')
    return ','.join(permissions)
