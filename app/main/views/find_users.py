from flask import render_template, request
from flask_login import login_required

from app import user_api_client
from app.main import main
from app.main.forms import SearchUsersByEmailForm
from app.models.user import User
from app.utils import user_is_platform_admin


@main.route("/find-users-by-email", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def find_users_by_email():
    form = SearchUsersByEmailForm()
    users_found = None
    status = 200
    if form.validate_on_submit():
        users_found = user_api_client.find_users_by_full_or_partial_email(form.search.data)['data']
    elif request.method == 'POST':
        status = 400
    return render_template(
        'views/find-users/find-users-by-email.html',
        form=form,
        users_found=users_found
    ), status


@main.route("/users/<user_id>", methods=['GET'])
@login_required
@user_is_platform_admin
def user_information(user_id):
    user = User.from_id(user_id)
    services = user_api_client.get_services_for_user(user)
    return render_template(
        'views/find-users/user-information.html',
        user=user,
        services=services,
    )
