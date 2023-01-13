from flask import abort, current_app, redirect, render_template, request, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError

from app import email_branding_client
from app.event_handlers import create_update_email_branding_event
from app.formatters import email_safe
from app.main import main
from app.main.forms import (
    AdminEditEmailBrandingForm,
    GovernmentIdentityCoatOfArmsOrInsignia,
    GovernmentIdentityColour,
    SearchByNameForm,
)
from app.models.branding import (
    GOVERNMENT_IDENTITY_SYSTEM_CRESTS_OR_INSIGNIA,
    INSIGNIA_ASSETS_PATH,
    AllEmailBranding,
    EmailBranding,
)
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
def platform_admin_update_email_branding(branding_id, logo=None):
    email_branding = EmailBranding.from_id(branding_id)

    form = AdminEditEmailBrandingForm(obj=email_branding)

    logo = logo or email_branding.logo

    if form.validate_on_submit():
        if form.file.data:
            upload_filename = upload_email_logo(
                form.file.data.filename, form.file.data, current_app.config["AWS_REGION"], user_id=current_user.id
            )

            if logo and logo.startswith(TEMP_TAG.format(user_id=current_user.id)):
                delete_email_temp_file(logo)

            return redirect(
                url_for(".platform_admin_update_email_branding", branding_id=branding_id, logo=upload_filename)
            )

        updated_logo_name = permanent_email_logo_name(logo, current_user.id) if logo else None

        try:
            email_branding_client.update_email_branding(
                branding_id=branding_id,
                logo=updated_logo_name,
                name=form.name.data,
                alt_text=form.alt_text.data,
                text=form.text.data,
                colour=form.colour.data,
                brand_type=form.brand_type.data,
                updated_by_id=current_user.id,
            )
            create_update_email_branding_event(
                email_branding_id=branding_id,
                updated_by_id=str(current_user.id),
                old_email_branding=email_branding.serialize(),
            )
        except HTTPError as e:
            if e.status_code == 400 and "name" in e.response.json().get("message", {}):
                form.name.errors.append(e.response.json()["message"]["name"][0])
            else:
                raise e

        if logo:
            persist_logo(logo, updated_logo_name)

        delete_email_temp_files_created_by(current_user.id)

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


@main.route("/email-branding/create-government-identity/logo", methods=["GET", "POST"])
@user_is_platform_admin
def create_email_branding_government_identity_logo():
    form = GovernmentIdentityCoatOfArmsOrInsignia()

    if form.validate_on_submit():
        return redirect(
            url_for(
                ".create_email_branding_government_identity_colour",
                text=request.args.get("text"),
                filename=form.coat_of_arms_or_insignia.data,
                brand_type=request.args.get("brand_type"),
            )
        )

    return render_template(
        "views/email-branding/government-identity-options.html",
        form=form,
    )


@main.route("/email-branding/create-government-identity/colour", methods=["GET", "POST"])
@user_is_platform_admin
def create_email_branding_government_identity_colour():

    filename = request.args.get("filename")
    if filename not in GOVERNMENT_IDENTITY_SYSTEM_CRESTS_OR_INSIGNIA:
        abort(400)

    filename = f"{filename}.png"
    form = GovernmentIdentityColour(crest_or_insignia_image_filename=filename)

    if form.validate_on_submit():
        image_file = INSIGNIA_ASSETS_PATH / filename
        upload_filename = upload_email_logo(
            email_safe(filename),
            image_file.resolve().read_bytes(),
            current_app.config["AWS_REGION"],
            user_id=current_user.id,
        )
        return redirect(
            url_for(
                "main.platform_admin_create_email_branding",
                name=request.args.get("text"),
                text=request.args.get("text"),
                colour=form.colour.data,
                logo=upload_filename,
                brand_type=request.args.get("brand_type"),
            )
        )

    return render_template(
        "views/email-branding/government-identity-options-colour.html",
        form=form,
    )


@main.route("/email-branding/create", methods=["GET", "POST"])
@main.route("/email-branding/create/<logo>", methods=["GET", "POST"])
@user_is_platform_admin
def platform_admin_create_email_branding(logo=None):
    form = AdminEditEmailBrandingForm(
        name=request.args.get("name"),
        text=request.args.get("text"),
        colour=request.args.get("colour"),
        brand_type=request.args.get("brand_type", "org"),
    )

    if form.validate_on_submit():
        if form.file.data:
            upload_filename = upload_email_logo(
                form.file.data.filename, form.file.data, current_app.config["AWS_REGION"], user_id=current_user.id
            )

            if logo and logo.startswith(TEMP_TAG.format(user_id=current_user.id)):
                delete_email_temp_file(logo)

            return redirect(url_for("main.platform_admin_create_email_branding", logo=upload_filename))

        updated_logo_name = permanent_email_logo_name(logo, current_user.id) if logo else None

        try:
            email_branding_client.create_email_branding(
                logo=updated_logo_name,
                name=form.name.data,
                alt_text=form.alt_text.data,
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

        delete_email_temp_files_created_by(current_user.id)

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
