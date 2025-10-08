from flask import abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError

from app import current_service, service_api_client
from app.constants import SERVICE_JOIN_REQUEST_APPROVED, SERVICE_JOIN_REQUEST_REJECTED
from app.event_handlers import Events
from app.formatters import redact_mobile_number
from app.main import main
from app.main.forms import (
    ChangeEmailForm,
    ChangeMobileNumberForm,
    ChangeNonGovEmailForm,
    InviteUserForm,
    JoinServiceRequestApproveForm,
    PermissionsForm,
    SearchUsersForm,
)
from app.models.service import Service, ServiceJoinRequest
from app.models.user import InvitedUser, User
from app.utils.user import is_gov_user, user_has_permissions
from app.utils.user_permissions import permission_options, translate_permissions_from_ui_to_db


@main.route("/services/<uuid:service_id>/users")
@user_has_permissions(allow_org_user=True)
def manage_users(service_id):
    return render_template(
        "views/manage-users.html",
        users=current_service.team_members,
        current_user=current_user,
        show_search_box=(len(current_service.team_members) > 7),
        form=SearchUsersForm(),
        permissions=permission_options,
    )


@main.route("/services/<uuid:service_id>/users/invite", methods=["GET", "POST"])
@main.route("/services/<uuid:service_id>/users/invite/<uuid:user_id>", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def invite_user(service_id, user_id=None):
    form = InviteUserForm(
        inviter_email_address=current_user.email_address,
        all_template_folders=current_service.all_template_folders,
        folder_permissions=[f["id"] for f in current_service.all_template_folders],
    )

    if user_id:
        user_to_invite = User.from_id(user_id)
        if user_to_invite.belongs_to_service(current_service.id):
            return render_template(
                "views/user-already-team-member.html",
                user_to_invite=user_to_invite,
            )
        if current_service.invite_pending_for(user_to_invite.email_address):
            return render_template(
                "views/user-already-invited.html",
                user_to_invite=user_to_invite,
            )
        if not user_to_invite.default_organisation:
            abort(403)
        if user_to_invite.default_organisation.id != current_service.organisation_id:
            abort(403)
        form.email_address.data = user_to_invite.email_address
    else:
        user_to_invite = None

    if not current_service.has_permission("email_auth"):
        form.login_authentication.data = "sms_auth"

    if form.validate_on_submit():
        email_address = form.email_address.data
        invited_user = InvitedUser.create(
            current_user.id,
            service_id,
            email_address,
            form.permissions,
            form.login_authentication.data,
            form.folder_permissions.data,
        )

        flash(f"Uitnodiging verstuurd naar {invited_user.email_address}", "default_with_tick")
        return redirect(url_for(".manage_users", service_id=service_id))

    return render_template(
        "views/invite-user.html",
        form=form,
        mobile_number=True,
        user_to_invite=user_to_invite,
        error_summary_enabled=True,
    )


def validate_service_join_request(service_id, request_id):
    service_join_request = ServiceJoinRequest.from_id(request_id, service_id)
    requested_by = service_join_request.requester
    request_changed_by = service_join_request.status_changed_by
    requested_service = Service.from_id(service_join_request.service_id)

    if not requested_service.organisation.can_ask_to_join_a_service:
        abort(403)

    if requested_service.organisation != current_user.default_organisation:
        abort(403)

    if current_user.id not in service_join_request.contacted_service_users:
        abort(403)

    if service_join_request.is_approved:
        return render_template(
            "views/service-join-request-already-approved.html",
            approved_by=request_changed_by,
            requested_by=requested_by,
            approved_at=service_join_request.status_changed_at,
            requested_service=requested_service,
        )
    if service_join_request.is_rejected:
        return render_template(
            "views/service-join-request-rejected.html",
            rejected_by=request_changed_by,
            requested_by=requested_by,
            rejected_at=service_join_request.status_changed_at,
        )
    if service_id in requested_by["belongs_to_service"]:
        return render_template(
            "views/service-join-request-user-already-joined.html",
            user_to_invite=requested_by,
        )


@main.route("/services/<uuid:service_id>/join-request/<uuid:request_id>/approve", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_join_request_approve(service_id, request_id):
    join_request_validation = validate_service_join_request(service_id, request_id)
    if join_request_validation:
        return join_request_validation

    form = JoinServiceRequestApproveForm()
    service_join_request = ServiceJoinRequest.from_id(request_id, service_id)
    requested_by = service_join_request.requester
    requested_service = Service.from_id(service_join_request.service_id)

    if form.validate_on_submit():
        if form.join_service_approve_request.data == SERVICE_JOIN_REQUEST_APPROVED:
            return redirect(
                url_for(
                    "main.service_join_request_choose_permissions",
                    service_id=service_id,
                    request_id=request_id,
                )
            )

        if form.join_service_approve_request.data == SERVICE_JOIN_REQUEST_REJECTED:
            return redirect(
                url_for(
                    "main.service_join_request_refused",
                    service_id=service_id,
                    request_id=request_id,
                )
            )

    return render_template(
        "views/join-service-request-approver.html",
        form=form,
        requester=requested_by,
        requested_service=requested_service,
        error_summary_enabled=True,
        service_id=service_id,
        request_id=request_id,
    )


@main.route("/services/<uuid:service_id>/join-request/<uuid:request_id>/choose-permissions", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_join_request_choose_permissions(service_id, request_id):
    join_request_validation = validate_service_join_request(service_id, request_id)
    if join_request_validation:
        return join_request_validation

    service_join_request = ServiceJoinRequest.from_id(request_id, service_id)

    requested_by = service_join_request.requester
    requested_by_user = User.from_id(requested_by["id"])

    form = PermissionsForm.from_user_and_service(requested_by_user, current_service)

    if form.validate_on_submit():
        update_kwargs = {
            "status": SERVICE_JOIN_REQUEST_APPROVED,
            "status_changed_by_id": current_user.id,
            "permissions": translate_permissions_from_ui_to_db(form.permissions_field.data),
            "folder_permissions": form.folder_permissions.data,
        }

        # Only change the auth type if this is supported for a service. If a user logs in with a
        # security key, we generally don't want them to be able to use something less secure.
        if current_service.has_permission("email_auth") and not requested_by_user.webauthn_auth:
            update_kwargs["auth_type"] = form.login_authentication.data

        service_join_request.update(**update_kwargs)

        flash(f"{requested_by_user.name} is lid geworden van deze dienst", "default_with_tick")
        return redirect(url_for(".manage_users", service_id=service_id))

    return render_template(
        "views/join-service-request-choose-permissions.html",
        form=form,
        request_id=request_id,
        requester=requested_by,
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/join-request/<uuid:request_id>/refused", methods=["GET"])
@user_has_permissions("manage_service")
def service_join_request_refused(service_id, request_id):
    join_request_validation = validate_service_join_request(service_id, request_id)
    if join_request_validation:
        return join_request_validation

    service_join_request = ServiceJoinRequest.from_id(request_id, service_id)
    requested_by = service_join_request.requester

    service_join_request.update(
        status=SERVICE_JOIN_REQUEST_REJECTED,
        status_changed_by_id=current_user.id,
    )

    return render_template(
        "views/join-service-request-refused.html",
        request_id=request_id,
        requester=requested_by,
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/users/<uuid:user_id>", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def edit_user_permissions(service_id, user_id):
    user = current_service.get_team_member(user_id)
    form = PermissionsForm.from_user_and_service(user, current_service)

    if form.validate_on_submit():
        user.set_permissions(
            service_id,
            permissions=form.permissions,
            folder_permissions=form.folder_permissions.data,
            set_by_id=current_user.id,
        )
        # Only change the auth type if this is supported for a service. If a user logs in with a
        # security key, we generally don't want them to be able to use something less secure.
        if current_service.has_permission("email_auth") and not user.webauthn_auth:
            user.update(auth_type=form.login_authentication.data)
        return redirect(url_for(".manage_users", service_id=service_id))

    return render_template(
        "views/edit-user-permissions.html",
        user=user,
        form=form,
        delete=request.args.get("delete"),
    )


@main.route("/services/<uuid:service_id>/users/<uuid:user_id>/delete", methods=["POST"])
@user_has_permissions("manage_service")
def remove_user_from_service(service_id, user_id):
    try:
        service_api_client.remove_user_from_service(service_id, user_id)
    except HTTPError as e:
        msg = "U kunt de laatste gebruiker van een organisatie niet verwijderen"
        if e.status_code == 400 and msg in e.message:
            flash(msg, "info")
            return redirect(url_for(".manage_users", service_id=service_id))
        else:
            abort(500, e)
    else:
        Events.remove_user_from_service(user_id=user_id, removed_by_id=current_user.id, service_id=service_id)

    return redirect(url_for(".manage_users", service_id=service_id))


@main.route("/services/<uuid:service_id>/users/<uuid:user_id>/edit-email", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def edit_user_email(service_id, user_id):
    user = current_service.get_team_member(user_id)
    user_email = user.email_address
    session_key = f"team_member_email_change-{user_id}"

    if is_gov_user(user_email):
        form = ChangeEmailForm(User.already_registered, email_address=user_email)
    else:
        form = ChangeNonGovEmailForm(User.already_registered, email_address=user_email)

    if request.form.get("email_address", "").strip() == user_email:
        return redirect(url_for(".manage_users", service_id=current_service.id))

    if form.validate_on_submit():
        session[session_key] = form.email_address.data

        return redirect(url_for(".confirm_edit_user_email", user_id=user.id, service_id=service_id))

    return render_template(
        "views/manage-users/edit-user-email.html",
        user=user,
        form=form,
        service_id=service_id,
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/users/<uuid:user_id>/edit-email/confirm", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def confirm_edit_user_email(service_id, user_id):
    user = current_service.get_team_member(user_id)
    session_key = f"team_member_email_change-{user_id}"
    if session_key in session:
        new_email = session[session_key]
    else:
        return redirect(url_for(".edit_user_email", service_id=service_id, user_id=user_id))
    if request.method == "POST":
        try:
            user.update(email_address=new_email, updated_by=current_user.id)
        except HTTPError as e:
            abort(500, e)
        else:
            Events.update_user_email(
                user_id=user.id,
                updated_by_id=current_user.id,
                original_email_address=user.email_address,
                new_email_address=new_email,
            )
        finally:
            session.pop(session_key, None)

        return redirect(url_for(".manage_users", service_id=service_id))
    return render_template(
        "views/manage-users/confirm-edit-user-email.html", user=user, service_id=service_id, new_email=new_email
    )


@main.route("/services/<uuid:service_id>/users/<uuid:user_id>/edit-mobile-number", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def edit_user_mobile_number(service_id, user_id):
    user = current_service.get_team_member(user_id)
    user_mobile_number = redact_mobile_number(user.mobile_number)

    form = ChangeMobileNumberForm(mobile_number=user_mobile_number)
    if form.mobile_number.data == user_mobile_number and request.method == "POST":
        return redirect(url_for(".manage_users", service_id=service_id))
    if form.validate_on_submit():
        session["team_member_mobile_change"] = form.mobile_number.data

        return redirect(url_for(".confirm_edit_user_mobile_number", user_id=user.id, service_id=service_id))
    return render_template(
        "views/manage-users/edit-user-mobile.html",
        user=user,
        form=form,
        service_id=service_id,
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/users/<uuid:user_id>/edit-mobile-number/confirm", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def confirm_edit_user_mobile_number(service_id, user_id):
    user = current_service.get_team_member(user_id)
    if "team_member_mobile_change" in session:
        new_number = session["team_member_mobile_change"]
    else:
        return redirect(url_for(".edit_user_mobile_number", service_id=service_id, user_id=user_id))
    if request.method == "POST":
        try:
            user.update(mobile_number=new_number, updated_by=current_user.id)
        except HTTPError as e:
            abort(500, e)
        else:
            Events.update_user_mobile_number(
                user_id=user.id,
                updated_by_id=current_user.id,
                original_mobile_number=user.mobile_number,
                new_mobile_number=new_number,
            )
        finally:
            session.pop("team_member_mobile_change", None)

        return redirect(url_for(".manage_users", service_id=service_id))

    return render_template(
        "views/manage-users/confirm-edit-user-mobile-number.html",
        user=user,
        service_id=service_id,
        new_mobile_number=new_number,
    )


@main.route("/services/<uuid:service_id>/cancel-invited-user/<uuid:invited_user_id>", methods=["GET"])
@user_has_permissions("manage_service")
def cancel_invited_user(service_id, invited_user_id):
    current_service.cancel_invite(invited_user_id)

    invited_user = InvitedUser.by_id_and_service_id(service_id, invited_user_id)

    flash(f"Uitnodiging geannuleerd voor {invited_user.email_address}", "default_with_tick")
    return redirect(url_for("main.manage_users", service_id=service_id))
