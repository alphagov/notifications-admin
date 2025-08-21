from flask import abort, flash, redirect, render_template, session, url_for
from flask_login import current_user
from markupsafe import Markup

from app.main import main
from app.models.organisation import Organisation
from app.models.service import Service
from app.models.user import InvitedOrgUser, InvitedUser, OrganisationUsers, User, Users


@main.route("/invitation/<string:token>")
def accept_invite(token):
    invited_user = InvitedUser.from_token(token)

    if not current_user.is_anonymous and current_user.email_address.lower() != invited_user.email_address.lower():
        message = Markup(
            """
            U bent aangemeld als {}.
            Deze uitnodiging is voor een ander e-mailadres.
            <a href={} class="govuk-link govuk-link--no-visited-state">Afmelden</a>
            en klik daarna opnieuw op de link om deze uitnodiging te accepteren.
            """.format(current_user.email_address, url_for("main.sign_out"))
        )

        flash(message=message)

        abort(403)

    if invited_user.status == "cancelled":
        service = Service.from_id(invited_user.service)
        return render_template(
            "views/cancelled-invitation.html", from_user=invited_user.from_user.name, service_name=service.name
        )
    if invited_user.status == "accepted":
        session.pop("invited_user_id", None)
        service = Service.from_id(invited_user.service)
        return redirect(url_for("main.service_dashboard", service_id=invited_user.service))

    session["invited_user_id"] = invited_user.id

    existing_user = User.from_email_address_or_none(invited_user.email_address)

    if existing_user:
        existing_user.update_email_access_validated_at()
        invited_user.accept_invite()
        if existing_user in Users(invited_user.service):
            return redirect(url_for("main.service_dashboard", service_id=invited_user.service))
        else:
            service = Service.from_id(invited_user.service)
            # als de dienst waaraan u wordt toegevoegd het type verificatie kan wijzigen, controleer dan of dit kan;
            # als de gebruiker een Platformbeheerder is, laten we dit ongewijzigd om te voorkomen dat
            # iemand het verificatietype naar iets minder veilig kan wijzigen
            if service.has_permission("email_auth") and not existing_user.platform_admin:
                if invited_user.auth_type == "email_auth" or (
                    # ze hebben een telefoonnummer; we willen dat ze dit gaan gebruiken.
                    # als ze geen mobiel nummer hebben, negeren we deze optie uit de uitnodiging
                    existing_user.mobile_number and invited_user.auth_type == "sms_auth"
                ):
                    existing_user.update(auth_type=invited_user.auth_type)
            existing_user.add_to_service(
                service_id=invited_user.service,
                permissions=invited_user.permissions,
                folder_permissions=invited_user.folder_permissions,
                invited_by_id=invited_user.from_user.id,
            )
            return redirect(url_for("main.service_dashboard", service_id=service.id))
    else:
        return redirect(url_for("main.register_from_invite"))


@main.route("/organisation-invitation/<string:token>")
def accept_org_invite(token):
    invited_org_user = InvitedOrgUser.from_token(token)

    if not current_user.is_anonymous and current_user.email_address.lower() != invited_org_user.email_address.lower():
        message = Markup(
            """
            U bent aangemeld als {}.
            Deze uitnodiging is voor een ander e-mailadres.
            <a class="govuk-link govuk-link--no-visited-state" href={}>Afmelden</a>
            en klik daarna opnieuw op de link om deze uitnodiging te accepteren.
            """.format(current_user.email_address, url_for("main.sign_out"))
        )

        flash(message=message)

        abort(403)

    if invited_org_user.status == "cancelled":
        organisation = Organisation.from_id(invited_org_user.organisation)
        return render_template(
            "views/cancelled-invitation.html",
            from_user=invited_org_user.invited_by.name,
            organisation_name=organisation.name,
        )

    if invited_org_user.status == "accepted":
        session.pop("invited_org_user_id", None)
        return redirect(url_for("main.organisation_dashboard", org_id=invited_org_user.organisation))

    session["invited_org_user_id"] = invited_org_user.id

    existing_user = User.from_email_address_or_none(invited_org_user.email_address)
    organisation_users = OrganisationUsers(invited_org_user.organisation)

    if existing_user:
        existing_user.update_email_access_validated_at()
        invited_org_user.accept_invite()
        if existing_user not in organisation_users:
            existing_user.add_to_organisation(
                organisation_id=invited_org_user.organisation, permissions=invited_org_user.permissions
            )
        return redirect(url_for("main.organisation_dashboard", org_id=invited_org_user.organisation))
    else:
        return redirect(url_for("main.register_from_org_invite"))
