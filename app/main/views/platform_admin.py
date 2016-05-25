from flask import render_template
from flask_login import login_required

from app.main import main
from app.utils import user_has_permissions


@main.route("/platform-admin")
@login_required
@user_has_permissions(admin_override=True)
def platform_admin():
    return render_template(
        'views/platform-admin.html'
    )
