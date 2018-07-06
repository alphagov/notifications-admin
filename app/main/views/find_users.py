from flask import abort, render_template, request, url_for
from flask_login import login_required

from app import user_api_client
from app.main import main
from app.utils import user_is_platform_admin
from app.main.forms import SearchUsersForm


@main.route("/find-users-by-email", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def find_users_by_email():
    form = SearchUsersForm()
    users_found = None
    if form.validate_on_submit():
        users_found = user_api_client.find_users_by_full_or_partial_email(form.search.data)['data']
    return render_template(
        'views/find-users/find-users-by-email.html',
        form=form,
        users_found=users_found
    )
