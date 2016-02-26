from flask import (
    request,
    render_template,
    redirect,
    abort,
    url_for,
    flash
)

from flask_login import (
    login_required,
    current_user
)

from notifications_python_client.errors import HTTPError

from app.main import main
from app.main.forms import InviteUserForm
from app.main.dao.services_dao import get_service_by_id_or_404
from app import user_api_client
from app import invite_api_client

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
def manage_users(service_id):
    users = user_api_client.get_users_for_service(service_id=service_id)
    return render_template(
        'views/manage-users.html',
        service_id=service_id,
        users=users,
        current_user=current_user,
        invited_users=[]
    )


@main.route("/services/<service_id>/users/invite", methods=['GET', 'POST'])
@login_required
def invite_user(service_id):

    form = InviteUserForm()
    if form.validate_on_submit():
        email_address = form.email_address.data
        try:
            resp = invite_api_client.create_invite(current_user.id, service_id, email_address)
            flash('Invite sent to {}'.format(resp['email_address']), 'default_with_tick')
            return redirect(url_for('.manage_users', service_id=service_id))

        except HTTPError as e:
            if e.status_code == 404:
                abort(404)
            else:
                raise e

    return render_template(
        'views/invite-user.html',
        user={},
        service=get_service_by_id_or_404(service_id),
        service_id=service_id,
        form=form
    )


@main.route("/services/<service_id>/users/<user_id>", methods=['GET', 'POST'])
@login_required
def edit_user(service_id, user_id):

    if request.method == 'POST':
        return redirect(url_for('.manage_users', service_id=service_id))

    return render_template(
        'views/invite-user.html',
        user=fake_users[int(user_id)],
        user_id=user_id,
        service=get_service_by_id_or_404(service_id),
        service_id=service_id
    )


@main.route("/services/<service_id>/users/<user_id>/delete", methods=['GET', 'POST'])
@login_required
def delete_user(service_id, user_id):

    if request.method == 'POST':
        return redirect(url_for('.manage_users', service_id=service_id))

    user = fake_users[int(user_id)]

    flash(
        'Are you sure you want to delete {}’s account?'.format(user.get('name') or user['email_localpart']),
        'delete'
    )

    return render_template(
        'views/invite-user.html',
        user=user,
        user_id=user_id,
        service=get_service_by_id_or_404(service_id),
        service_id=service_id
    )
