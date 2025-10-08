from botocore.exceptions import ClientError as BotoClientError
from flask import current_app, redirect, render_template, request, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError

from app import letter_branding_client, logo_client
from app.event_handlers import Events
from app.main import main
from app.main.forms import (
    AdminEditLetterBrandingForm,
    AdminEditLetterBrandingSVGUploadForm,
    SearchByNameForm,
)
from app.models.branding import AllLetterBranding, LetterBranding
from app.utils.branding import letter_filename_for_db_from_logo_key
from app.utils.user import user_is_platform_admin


@main.route("/letter-branding", methods=["GET"])
@user_is_platform_admin
def letter_branding():
    return render_template(
        "views/letter-branding/select-letter-branding.html",
        letter_brandings=AllLetterBranding(),
        _search_form=SearchByNameForm(),
    )


@main.route("/letter-branding/<uuid:branding_id>", methods=["GET", "POST"])
@user_is_platform_admin
def platform_admin_view_letter_branding(branding_id):
    letter_branding = LetterBranding.from_id(branding_id)

    return render_template(
        "views/letter-branding/view-branding.html",
        letter_branding=letter_branding,
        branding_orgs=letter_branding.organisations,
        branding_services=letter_branding.services,
    )


@main.route("/letter-branding/<uuid:branding_id>/edit", methods=["GET", "POST"])
@user_is_platform_admin
def update_letter_branding(branding_id):
    letter_branding = LetterBranding.from_id(branding_id)

    file_upload_form = AdminEditLetterBrandingSVGUploadForm()
    letter_branding_details_form = AdminEditLetterBrandingForm(
        name=letter_branding.name,
    )

    file_upload_form_submitted = file_upload_form.file.data
    details_form_submitted = request.form.get("operation") == "branding-details"

    logo_key = request.args.get(
        "logo_key", logo_client.get_logo_key(f"{letter_branding.filename}.svg", logo_type="letter")
    )
    logo_changed = "logo_key" in request.args

    if file_upload_form_submitted and file_upload_form.validate_on_submit():
        temporary_logo_key = logo_client.save_temporary_logo(
            file_upload_form.file.data,
            logo_type="letter",
        )

        return redirect(url_for(".update_letter_branding", branding_id=branding_id, logo_key=temporary_logo_key))

    if details_form_submitted and letter_branding_details_form.validate_on_submit():
        try:
            if logo_changed:
                permanent_logo_key = logo_client.save_permanent_logo(
                    logo_key, logo_type="letter", logo_key_extra=letter_branding_details_form.name.data
                )
                db_filename = letter_filename_for_db_from_logo_key(permanent_logo_key)
            else:
                db_filename = letter_branding.filename

            letter_branding_client.update_letter_branding(
                branding_id=branding_id,
                filename=db_filename,
                name=letter_branding_details_form.name.data,
                updated_by_id=current_user.id,
            )
            Events.update_letter_branding(
                letter_branding_id=branding_id,
                updated_by_id=current_user.id,
                old_letter_branding=letter_branding.serialize(),
            )

            return redirect(url_for("main.platform_admin_view_letter_branding", branding_id=letter_branding.id))

        except HTTPError as e:
            if "name" in e.message:
                letter_branding_details_form.name.errors.append(e.message["name"][0])
            else:
                raise e

        except BotoClientError:
            file_upload_form.file.errors = ["Error saving uploaded file - try uploading again"]

    return render_template(
        "views/letter-branding/manage-letter-branding.html",
        back_link=url_for("main.platform_admin_view_letter_branding", branding_id=letter_branding.id),
        file_upload_form=file_upload_form,
        letter_branding_details_form=letter_branding_details_form,
        cdn_url=current_app.config["LOGO_CDN_DOMAIN"],
        logo=logo_key,
        is_update=True,
        error_summary_enabled=True,
    )


@main.route("/letter-branding/create", methods=["GET", "POST"])
@user_is_platform_admin
def create_letter_branding():
    file_upload_form = AdminEditLetterBrandingSVGUploadForm()
    letter_branding_details_form = AdminEditLetterBrandingForm()

    file_upload_form_submitted = file_upload_form.file.data
    details_form_submitted = request.form.get("operation") == "branding-details"

    temporary_logo_key = request.args.get("logo_key")

    if file_upload_form_submitted and file_upload_form.validate_on_submit():
        temporary_logo_key = logo_client.save_temporary_logo(
            file_upload_form.file.data,
            logo_type="letter",
        )

        return redirect(url_for(".create_letter_branding", logo_key=temporary_logo_key))

    if details_form_submitted and letter_branding_details_form.validate_on_submit():
        if temporary_logo_key:
            try:
                permanent_logo_key = logo_client.save_permanent_logo(
                    temporary_logo_key,
                    logo_type="letter",
                    logo_key_extra=letter_branding_details_form.name.data,
                )
                letter_branding = LetterBranding.create(
                    filename=letter_filename_for_db_from_logo_key(permanent_logo_key),
                    name=letter_branding_details_form.name.data,
                )

                return redirect(url_for("main.platform_admin_view_letter_branding", branding_id=letter_branding.id))

            except HTTPError as e:
                if "name" in e.message:
                    letter_branding_details_form.name.errors.append(e.message["name"][0])
                else:
                    raise e
        else:
            # Show error on upload form if trying to submit with no logo
            file_upload_form.validate()

    return render_template(
        "views/letter-branding/manage-letter-branding.html",
        back_link=url_for("main.letter_branding"),
        file_upload_form=file_upload_form,
        letter_branding_details_form=letter_branding_details_form,
        cdn_url=current_app.config["LOGO_CDN_DOMAIN"],
        logo=temporary_logo_key,
        error_summary_enabled=True,
    )
