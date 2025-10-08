from io import BytesIO

from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError
from werkzeug.datastructures import FileStorage

from app import email_branding_client
from app.event_handlers import Events
from app.main import main
from app.main.forms import (
    AdminEditEmailBrandingForm,
    GovernmentIdentityCoatOfArmsOrInsignia,
    GovernmentIdentityColour,
    SearchByNameForm,
)
from app.models.branding import (
    AllEmailBranding,
    EmailBranding,
    get_government_identity_system_crests_or_insignia,
    get_insignia_asset_path,
)
from app.s3_client.logo_client import logo_client
from app.utils.user import user_is_platform_admin


@main.route("/email-branding", methods=["GET", "POST"])
@user_is_platform_admin
def email_branding():
    return render_template(
        "views/email-branding/select-branding.html", email_brandings=AllEmailBranding(), _search_form=SearchByNameForm()
    )


@main.route(
    "/email-branding/<uuid:branding_id>", methods=["GET", "POST"], endpoint="platform_admin_view_email_branding"
)
@main.route(
    "/email-branding/<uuid:branding_id>/archive",
    methods=["GET"],
    endpoint="platform_admin_confirm_archive_email_branding",
)
@user_is_platform_admin
def platform_admin_view_email_branding(branding_id):
    email_branding = EmailBranding.from_id(branding_id)

    if request.endpoint == "main.platform_admin_confirm_archive_email_branding":
        if email_branding.is_used_by_orgs_or_services:
            flash("This email branding is in use. You cannot delete it.")
        else:
            flash("Are you sure you want to delete this email branding?", "delete")

    return render_template(
        "views/email-branding/view-branding.html",
        email_branding=email_branding,
        cdn_url=current_app.config["LOGO_CDN_DOMAIN"],
        branding_orgs=email_branding.organisations,
        branding_services=email_branding.services,
    )


@main.route("/email-branding/<uuid:branding_id>/edit", methods=["GET", "POST"])
@user_is_platform_admin
def platform_admin_update_email_branding(branding_id):
    email_branding = EmailBranding.from_id(branding_id)

    form = AdminEditEmailBrandingForm(obj=email_branding)

    logo_key = request.args.get("logo_key", email_branding.logo)
    logo_changed = "logo_key" in request.args

    if form.validate_on_submit():
        if form.file.data:
            temporary_logo_key = logo_client.save_temporary_logo(
                form.file.data,
                logo_type="email",
            )
            return redirect(
                url_for(".platform_admin_update_email_branding", branding_id=branding_id, logo_key=temporary_logo_key)
            )

        permanent_logo_key = email_branding.logo
        if logo_changed:
            permanent_logo_key = logo_client.save_permanent_logo(
                logo_key, logo_type="email", logo_key_extra=form.name.data
            )

        try:
            email_branding_client.update_email_branding(
                branding_id=branding_id,
                logo=permanent_logo_key,
                name=form.name.data,
                alt_text=form.alt_text.data,
                text=form.text.data,
                colour=form.colour.data,
                brand_type=form.brand_type.data,
                updated_by_id=current_user.id,
            )
            Events.update_email_branding(
                email_branding_id=branding_id,
                updated_by_id=str(current_user.id),
                old_email_branding=email_branding.serialize(),
            )
        except HTTPError as e:
            if e.status_code == 400 and "name" in e.response.json().get("message", {}):
                form.name.errors.append(e.response.json()["message"]["name"][0])
            else:
                raise e

        if not form.errors:
            return redirect(url_for(".platform_admin_view_email_branding", branding_id=branding_id))

    return (
        render_template(
            "views/email-branding/manage-branding.html",
            form=form,
            email_branding=email_branding,
            cdn_url=current_app.config["LOGO_CDN_DOMAIN"],
            logo=logo_key,
            back_link=url_for("main.platform_admin_view_email_branding", branding_id=email_branding.id),
            error_summary_enabled=True,
        ),
        400 if form.errors else 200,
    )


@main.route("/email-branding/<uuid:branding_id>/archive", methods=["POST"])
@user_is_platform_admin
def platform_admin_archive_email_branding(branding_id):
    email_branding_client.archive_email_branding(branding_id=branding_id)
    return redirect(url_for(".email_branding"))


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
        error_summary_enabled=True,
    )


@main.route("/email-branding/create-government-identity/colour", methods=["GET", "POST"])
@user_is_platform_admin
def create_email_branding_government_identity_colour():
    filename = request.args.get("filename")
    if filename not in get_government_identity_system_crests_or_insignia():
        abort(400)

    filename = f"{filename}.png"
    form = GovernmentIdentityColour(crest_or_insignia_image_filename=filename)

    if form.validate_on_submit():
        image_file_path = get_insignia_asset_path() / filename
        logo_data = FileStorage(
            BytesIO(image_file_path.resolve().read_bytes()), filename=filename, content_type="image/png"
        )
        temporary_logo_key = logo_client.save_temporary_logo(
            logo_data,
            logo_type="email",
        )
        return redirect(
            url_for(
                "main.platform_admin_create_email_branding",
                name=request.args.get("text"),
                text=request.args.get("text"),
                colour=form.colour.data,
                logo_key=temporary_logo_key,
                brand_type=request.args.get("brand_type"),
                back="government-identity",
                government_identity=request.args.get("filename"),
            )
        )

    return render_template(
        "views/email-branding/government-identity-options-colour.html",
        form=form,
        error_summary_enabled=True,
    )


@main.route("/email-branding/create", methods=["GET", "POST"])
@user_is_platform_admin
def platform_admin_create_email_branding():
    form = AdminEditEmailBrandingForm(
        name=request.args.get("name"),
        text=request.args.get("text"),
        colour=request.args.get("colour"),
        brand_type=request.args.get("brand_type", "org"),
    )

    temporary_logo_key = request.args.get("logo_key")

    if form.validate_on_submit():
        if form.file.data:
            temporary_logo_key = logo_client.save_temporary_logo(
                form.file.data,
                logo_type="email",
            )
            return redirect(url_for("main.platform_admin_create_email_branding", logo_key=temporary_logo_key))

        permanent_logo_key = None
        if temporary_logo_key:
            permanent_logo_key = logo_client.save_permanent_logo(
                temporary_logo_key, logo_type="email", logo_key_extra=form.name.data
            )

        try:
            email_branding_client.create_email_branding(
                logo=permanent_logo_key,
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

        if not form.errors:
            return redirect(url_for(".email_branding"))

    if request.args.get("back") == "government-identity":
        back_link = url_for(
            "main.create_email_branding_government_identity_colour", filename=request.args.get("government_identity")
        )
    else:
        back_link = url_for("main.email_branding")

    return (
        render_template(
            "views/email-branding/manage-branding.html",
            form=form,
            cdn_url=current_app.config["LOGO_CDN_DOMAIN"],
            logo=temporary_logo_key,
            back_link=back_link,
            error_summary_enabled=True,
        ),
        400 if form.errors else 200,
    )
