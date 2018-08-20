from flask import current_app, redirect, render_template, session, url_for
from flask_login import login_required

from app import email_branding_client
from app.main import main
from app.main.forms import (
    ServiceCreateEmailBranding,
    ServiceSelectEmailBranding,
    ServiceUpdateEmailBranding,
)
from app.main.s3_client import (
    TEMP_TAG,
    delete_temp_file,
    delete_temp_files_created_by,
    persist_logo,
    upload_logo,
)
from app.main.views.service_settings import (
    get_branding_as_dict,
    get_branding_as_value_and_label,
)
from app.utils import get_cdn_domain, user_is_platform_admin


@main.route("/email-branding", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def email_branding():
    brandings = email_branding_client.get_all_email_branding(sort_key='name')

    form = ServiceSelectEmailBranding()
    email_brandings = get_branding_as_value_and_label(brandings)
    form.email_branding.choices = email_brandings + [('None', 'Create a new email branding')]

    if form.validate_on_submit():
        if form.email_branding.data != 'None':
            return redirect(url_for('.update_email_branding', branding_id=form.email_branding.data))
        else:
            return redirect(url_for('.create_email_branding'))

    return render_template(
        'views/email-branding/select-branding.html',
        form=form,
        branding_dict=get_branding_as_dict(brandings),
    )


@main.route("/email-branding/<branding_id>/edit", methods=['GET', 'POST'])
@main.route("/email-branding/<branding_id>/edit/<logo>", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def update_email_branding(branding_id, logo=None):
    email_branding = email_branding_client.get_email_branding(branding_id)['email_branding']

    form = ServiceUpdateEmailBranding()

    logo = logo if logo else email_branding.get('logo') if email_branding else None

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

            return redirect(url_for('.update_email_branding', branding_id=branding_id, logo=upload_filename))

        if logo:
            logo = persist_logo(logo, session["user_id"])

        delete_temp_files_created_by(session["user_id"])

        email_branding_client.update_email_branding(
            branding_id=branding_id,
            logo=logo,
            name=form.name.data,
            text=form.text.data,
            colour=form.colour.data,
            banner_colour=form.banner_colour.data,
            single_id_colour=form.single_id_colour.data,
            domain=form.domain.data,
        )

        return redirect(url_for('.email_branding', branding_id=branding_id))

    form.name.data = email_branding['name']
    form.text.data = email_branding['text']
    form.colour.data = email_branding['colour']
    form.banner_colour.data = email_branding['banner_colour']
    form.single_id_colour.data = email_branding['single_id_colour']
    form.domain.data = email_branding['domain']

    return render_template(
        'views/email-branding/manage-branding.html',
        form=form,
        email_branding=email_branding,
        cdn_url=get_cdn_domain(),
        logo=logo
    )


@main.route("/email-branding/create", methods=['GET', 'POST'])
@main.route("/email-branding/create/<logo>", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def create_email_branding(logo=None):
    form = ServiceCreateEmailBranding()

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

            return redirect(url_for('.create_email_branding', logo=upload_filename))

        if logo:
            logo = persist_logo(logo, session["user_id"])

        delete_temp_files_created_by(session["user_id"])

        email_branding_client.create_email_branding(
            logo=logo,
            name=form.name.data,
            text=form.text.data,
            colour=form.colour.data,
            banner_colour=form.banner_colour.data,
            single_id_colour=form.single_id_colour.data,
            domain=form.domain.data
        )

        return redirect(url_for('.email_branding'))

    return render_template(
        'views/email-branding/manage-branding.html',
        form=form,
        cdn_url=get_cdn_domain(),
        logo=logo
    )
