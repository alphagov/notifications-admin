from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError

from app import user_api_client
from app.event_handlers import create_archive_user_event
from app.main import main
from app.main.forms import AdminSearchUsersByEmailForm, AuthTypeForm
from app.models.user import User
from app.utils.user import user_is_platform_admin


@main.route("/find-users-by-email", methods=['GET', 'POST'])
@user_is_platform_admin
def find_users_by_email():
    form = AdminSearchUsersByEmailForm()
    users_found = None
    if form.validate_on_submit():
        users_found = user_api_client.find_users_by_full_or_partial_email(form.search.data)['data']
    return render_template(
        'views/find-users/find-users-by-email.html',
        form=form,
        users_found=users_found
    )


@main.route("/users/<uuid:user_id>", methods=['GET'])
@user_is_platform_admin
def user_information(user_id):
    return render_template(
        'views/find-users/user-information.html',
        user=User.from_id(user_id),
    )


@main.route("/users/<uuid:user_id>/archive", methods=['GET', 'POST'])
@user_is_platform_admin
def archive_user(user_id):
    if request.method == 'POST':
        try:
            user_api_client.archive_user(user_id)
        except HTTPError as e:
            if e.status_code == 400 and 'manage_settings' in e.message:
                flash('User can’t be removed from a service - '
                      'check all services have another team member with manage_settings')
                return redirect(url_for('main.user_information', user_id=user_id))
        create_archive_user_event(user_id=str(user_id), archived_by_id=current_user.id)

        return redirect(url_for('.user_information', user_id=user_id))
    else:
        flash('There\'s no way to reverse this! Are you sure you want to archive this user?', 'delete')
        return user_information(user_id)


@main.route("/users/<uuid:user_id>/change_auth", methods=['GET', 'POST'])
@user_is_platform_admin
def change_user_auth(user_id):
    user = User.from_id(user_id)
    if user.webauthn_auth:
        abort(403)

    form = AuthTypeForm(auth_type=user.auth_type)

    if form.validate_on_submit():
        user.update(auth_type=form.auth_type.data)
        return redirect(url_for('.user_information', user_id=user_id))

    return render_template(
        'views/find-users/auth_type.html',
        form=form,
        user=user,
    )
