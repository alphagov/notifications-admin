from flask import redirect, render_template, url_for
from flask_login import login_required

from app import organisations_client
from app.main import main
from app.main.forms import CreateOrUpdateOrganisation
from app.utils import user_has_permissions


@main.route("/organisations", methods=['GET'])
@login_required
@user_has_permissions(admin_override=True)
def organisations():
    orgs = organisations_client.get_organisations()

    return render_template(
        'views/organisations/index.html',
        organisations=orgs
    )


@main.route("/organisations/add", methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
def add_organisation():
    form = CreateOrUpdateOrganisation()

    if form.validate_on_submit():
        organisations_client.create_organisation(
            name=form.name.data,
        )

        return redirect(url_for('.organisations'))

    return render_template(
        'views/organisations/add-organisation.html',
        form=form
    )


@main.route("/organisation/<org_id>", methods=['GET'])
@login_required
@user_has_permissions(admin_override=True)
def organisation_dashboard(org_id):
    organisation_services = organisations_client.get_organisation_services(org_id)

    return render_template(
        'views/organisations/organisation/index.html',
        organisation_services=organisation_services
    )


@main.route("/organisation/<org_id>/edit", methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
def update_organisation(org_id):
    org = organisations_client.get_organisation(org_id)

    form = CreateOrUpdateOrganisation()

    if form.validate_on_submit():
        organisations_client.update_organisation(
            org_id=org_id,
            name=form.name.data
        )

        return redirect(url_for('.organisations'))

    form.name.data = org['name']

    return render_template(
        'views/organisations/organisation/update-organisation.html',
        form=form,
        organisation=org
    )


@main.route("/organisation/<org_id>/users", methods=['GET'])
@login_required
@user_has_permissions(admin_override=True)
def organisation_users(org_id):

    return render_template(
        'views/organisations/organisation/users/index.html',
    )
