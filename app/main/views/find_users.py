from flask import abort, render_template, request, url_for
from flask_login import login_required

from app import user_api_client
from app.main import main
from app.utils import user_is_platform_admin
from app.main.forms import SearchUsersByEmailForm


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
