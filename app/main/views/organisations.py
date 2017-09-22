from flask import current_app, redirect, render_template, session, url_for, request
from flask_login import login_required

from app import organisations_client
from app.main import main
from app.main.forms import (
    ServiceSelectOrg,
    ServiceManageOrg)
from app.utils import user_has_permissions, get_cdn_domain
from app.main.s3_client import (
    TEMP_TAG,
    upload_logo,
    delete_temp_file,
    delete_temp_files_created_by,
    persist_logo
)
from app.main.views.service_settings import get_branding_as_value_and_label, get_branding_as_dict


@main.route("/organisations", methods=['GET', 'POST'])
@main.route("/organisations/<organisation_id>", methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
def organisations(organisation_id=None):
    orgs = organisations_client.get_organisations()

    form = ServiceSelectOrg()
    form.organisation.choices = get_branding_as_value_and_label(orgs) + [('None', 'Create a new organisation')]

    if form.validate_on_submit():
        if form.organisation.data != 'None':
            session['organisation'] = [o for o in orgs if o['id'] == form.organisation.data][0]
        elif session.get('organisation'):
            del session['organisation']

        return redirect(url_for('.manage_org'))

    form.organisation.data = organisation_id if organisation_id in [o['id'] for o in orgs] else 'None'

    return render_template(
        'views/organisations/select-org.html',
        form=form,
        branding_dict=get_branding_as_dict(orgs),
        organisation_id=organisation_id
    )


@main.route("/organisations/manage", methods=['GET', 'POST'])
@main.route("/organisations/manage/<logo>", methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
def manage_org(logo=None):
    form = ServiceManageOrg()

    org = session.get("organisation")

    logo = logo if logo else org.get('logo') if org else None

    if form.validate_on_submit():
        if form.file.data:
            upload_filename = upload_logo(
                form.file.data.filename,
                form.file.data,
                current_app.config['AWS_REGION'],
                user_id=session["user_id"]
            )

            if logo and logo.startswith(TEMP_TAG.format(user_id=session['user_id'])):
                delete_temp_file(logo)

            return redirect(
                url_for('.manage_org', logo=upload_filename))

        if logo:
            logo = persist_logo(logo, session["user_id"])

        delete_temp_files_created_by(session["user_id"])

        if org:
            organisations_client.update_organisation(
                org_id=org['id'], logo=logo, name=form.name.data, colour=form.colour.data)
            org_id = org['id']
        else:
            resp = organisations_client.create_organisation(
                logo=logo, name=form.name.data, colour=form.colour.data)
            org_id = resp['data']['id']

        return redirect(url_for('.organisations', organisation_id=org_id))
    if org:
        form.name.data = org['name']
        form.colour.data = org['colour']

    return render_template(
        'views/organisations/manage-org.html',
        form=form,
        organisation=org,
        cdn_url=get_cdn_domain(),
        logo=logo
    )
