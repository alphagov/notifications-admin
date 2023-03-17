from flask import redirect, render_template, url_for

from app import current_user
from app.main import main
from app.main.forms import JoinServiceForm
from app.models.service import Service
from app.utils.user import user_is_gov_user, user_is_logged_in


@main.route("/services/<uuid:service_to_join_id>/join", methods=["GET", "POST"])
@user_is_logged_in
@user_is_gov_user
def join_service(service_to_join_id):
    service = Service.from_id(service_to_join_id)
    form = JoinServiceForm(
        users=service.active_users_with_permission("manage_service"),
    )
    if form.validate_on_submit():
        service.request_invite_for(
            current_user,
            from_user_ids=form.users.data,
            reason=form.reason.data,
        )
        return redirect(
            url_for(
                "main.join_service_requested",
                service_to_join_id=service.id,
                number_of_users_emailed=len(form.users.data),
            )
        )

    return render_template(
        "views/join-service.html",
        service=service,
        form=form,
    )


@main.route("/services/<uuid:service_to_join_id>/join/requested", methods=["GET", "POST"])
@user_is_logged_in
@user_is_gov_user
def join_service_requested(service_to_join_id):
    service = Service.from_id(service_to_join_id)
    return render_template(
        "views/join-service-requested.html",
        service=service,
    )
