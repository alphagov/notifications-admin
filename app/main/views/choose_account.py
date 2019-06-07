from flask import redirect, render_template, session, url_for
from flask_login import current_user, login_required

from app.main import main
from app.utils import PermanentRedirect


@main.route("/services")
def choose_service():
    raise PermanentRedirect(url_for('.choose_account'))


@main.route("/services-or-dashboard")
def services_or_dashboard():
    raise PermanentRedirect(url_for('.show_accounts_or_dashboard'))


@main.route("/accounts")
@login_required
def choose_account():
    return render_template(
        'views/choose-account.html',
        can_add_service=current_user.is_gov_user,
    )


@main.route("/accounts-or-dashboard")
def show_accounts_or_dashboard():

    if not current_user.is_authenticated:
        return redirect(url_for('.index'))

    service_id = session.get('service_id')
    if service_id and (service_id in current_user.services or current_user.platform_admin):
        return redirect(url_for('.service_dashboard', service_id=service_id))

    organisation_id = session.get('organisation_id')
    if organisation_id and (organisation_id in current_user.organisation_ids or current_user.platform_admin):
        return redirect(url_for('.organisation_dashboard', org_id=organisation_id))

    if len(current_user.services) == 1 and not current_user.organisation_ids:
        return redirect(url_for('.service_dashboard', service_id=current_user.services[0]))

    if len(current_user.organisation_ids) == 1 and not current_user.services:
        return redirect(url_for('.organisation_dashboard', org_id=current_user.organisation_ids[0]))

    return redirect(url_for('.choose_account'))
