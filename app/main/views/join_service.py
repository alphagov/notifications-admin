from flask import render_template

from app.main import main
from app.utils.user import user_is_gov_user, user_is_logged_in


@main.route("/services/<uuid:service_to_join_id>/join", methods=["GET", "POST"])
@user_is_logged_in
@user_is_gov_user
def join_service(service_to_join_id):
    return render_template("views/join-service.html")
