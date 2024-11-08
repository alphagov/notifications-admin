from flask import abort, redirect, render_template, url_for

from app import current_user
from app.main import main
from app.main.forms import JoinServiceForm, SearchByNameForm
from app.models.service import Service
from app.utils.user import user_is_gov_user, user_is_logged_in


@main.route("/join-a-service/choose", methods=["GET", "POST"])
@user_is_logged_in
@user_is_gov_user
def join_service_choose_service():
    if not current_user.default_organisation.can_ask_to_join_a_service:
        abort(403)

    return render_template(
        "views/join-a-service/choose-a-service.html",
        _search_form=SearchByNameForm(),
    )


@main.route("/services/<uuid:service_to_join_id>/join/ask", methods=["GET", "POST"])
@user_is_logged_in
@user_is_gov_user
def join_service_ask(service_to_join_id):
    service = Service.from_id(service_to_join_id)

    if not service.organisation.can_ask_to_join_a_service:
        abort(403)

    if service.organisation != current_user.default_organisation:
        abort(403)

    form = JoinServiceForm(
        users=service.active_users_with_permission("manage_service"),
    )
    if form.validate_on_submit():
        service.request_invite_for(
            current_user,
            service_managers_ids=form.users.data,
            reason=form.reason.data,
        )
        return redirect(
            url_for(
                "main.join_service_you_have_asked",
                service_to_join_id=service.id,
                number_of_users_emailed=len(form.users.data),
            )
        )

    return render_template(
        "views/join-a-service/ask.html",
        service=service,
        form=form,
    )


@main.route("/services/<uuid:service_to_join_id>/join/you-have-asked", methods=["GET", "POST"])
@user_is_logged_in
@user_is_gov_user
def join_service_you_have_asked(service_to_join_id):
    service = Service.from_id(service_to_join_id)
    return render_template(
        "views/join-a-service/you-have-asked.html",
        service=service,
    )
