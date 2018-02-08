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
        'views/organisations/organisations.html',
        organisations=orgs
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
        'views/organisations/manage-organisation.html',
        form=form,
        organisation=org
    )


@main.route("/organisations/create", methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
def create_organisation():
    form = CreateOrUpdateOrganisation()

    if form.validate_on_submit():
        organisations_client.create_organisation(
            name=form.name.data,
        )

        return redirect(url_for('.organisations'))

    return render_template(
        'views/organisations/manage-organisation.html',
        form=form
    )
