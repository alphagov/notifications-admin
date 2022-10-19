from flask import current_app, redirect, render_template, session, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError

from app import email_branding_client
from app.event_handlers import create_update_email_branding_event
from app.main import main
from app.main.forms import AdminEditEmailBrandingForm, SearchByNameForm
from app.models.branding import AllEmailBranding, EmailBranding
from app.s3_client.s3_logo_client import (
    TEMP_TAG,
    delete_email_temp_file,
    delete_email_temp_files_created_by,
    permanent_email_logo_name,
    persist_logo,
    upload_email_logo,
)
from app.utils.user import user_is_platform_admin


@main.route("/email-branding", methods=["GET", "POST"])
@user_is_platform_admin
def email_branding():
    return render_template(
        "views/email-branding/select-branding.html", email_brandings=AllEmailBranding(), search_form=SearchByNameForm()
    )


@main.route("/email-branding/<uuid:branding_id>/edit", methods=["GET", "POST"])
@main.route("/email-branding/<uuid:branding_id>/edit/<logo>", methods=["GET", "POST"])
@user_is_platform_admin
def update_email_branding(branding_id, logo=None):
    email_branding = EmailBranding.from_id(branding_id)

    form = AdminEditEmailBrandingForm(
        name=email_branding.name,
        text=email_branding.text,
        colour=email_branding.colour,
        brand_type=email_branding.brand_type,
    )

    logo = logo or email_branding.logo

    if form.validate_on_submit():
        if form.file.data:
            upload_filename = upload_email_logo(
                form.file.data.filename, form.file.data, current_app.config["AWS_REGION"], user_id=session["user_id"]
            )

            if logo and logo.startswith(TEMP_TAG.format(user_id=session["user_id"])):
                delete_email_temp_file(logo)

            return redirect(url_for(".update_email_branding", branding_id=branding_id, logo=upload_filename))

        updated_logo_name = permanent_email_logo_name(logo, session["user_id"]) if logo else None

        try:
            email_branding_client.update_email_branding(
                branding_id=branding_id,
                logo=updated_logo_name,
                name=form.name.data,
                text=form.text.data,
                colour=form.colour.data,
                brand_type=form.brand_type.data,
                updated_by_id=current_user.id,
            )
            create_update_email_branding_event(
                email_branding_id=branding_id, updated_by_id=str(current_user.id), old_email_branding=email_branding
            )
        except HTTPError as e:
            if e.status_code == 400 and "name" in e.response.json().get("message", {}):
                form.name.errors.append(e.response.json()["message"]["name"][0])
            else:
                raise e

        if logo:
            persist_logo(logo, updated_logo_name)

        delete_email_temp_files_created_by(session["user_id"])

        if not form.errors:
            return redirect(url_for(".email_branding", branding_id=branding_id))

    return (
        render_template(
            "views/email-branding/manage-branding.html",
            form=form,
            email_branding=email_branding,
            cdn_url=current_app.config["LOGO_CDN_DOMAIN"],
            logo=logo,
        ),
        400 if form.errors else 200,
    )


@main.route("/email-branding/create", methods=["GET", "POST"])
@main.route("/email-branding/create/<logo>", methods=["GET", "POST"])
@user_is_platform_admin
def create_email_branding(logo=None):
    form = AdminEditEmailBrandingForm(brand_type="org")

    if form.validate_on_submit():
        if form.file.data:
            upload_filename = upload_email_logo(
                form.file.data.filename, form.file.data, current_app.config["AWS_REGION"], user_id=session["user_id"]
            )

            if logo and logo.startswith(TEMP_TAG.format(user_id=session["user_id"])):
                delete_email_temp_file(logo)

            return redirect(url_for(".create_email_branding", logo=upload_filename))

        updated_logo_name = permanent_email_logo_name(logo, session["user_id"]) if logo else None

        try:
            email_branding_client.create_email_branding(
                logo=updated_logo_name,
                name=form.name.data,
                text=form.text.data,
                colour=form.colour.data,
                brand_type=form.brand_type.data,
                created_by_id=current_user.id,
            )
        except HTTPError as e:
            if e.status_code == 400 and "name" in e.response.json().get("message", {}):
                form.name.errors.append(e.response.json()["message"]["name"][0])
            else:
                raise e

        if logo:
            persist_logo(logo, updated_logo_name)

        delete_email_temp_files_created_by(session["user_id"])

        if not form.errors:
            return redirect(url_for(".email_branding"))

    return (
        render_template(
            "views/email-branding/manage-branding.html",
            form=form,
            cdn_url=current_app.config["LOGO_CDN_DOMAIN"],
            logo=logo,
        ),
        400 if form.errors else 200,
    )
