from flask import abort, render_template, request, url_for
from flask_login import login_required

from app.main import main
from app.utils import user_is_platform_admin
from app.main.forms import SearchUsersForm


@main.route("/find-users-by-email", methods=['GET'])
@login_required
@user_is_platform_admin
def find_users_by_email():
    return render_template(
        'views/find-users/find-users-by-email.html',
        form=SearchUsersForm(),
    )
