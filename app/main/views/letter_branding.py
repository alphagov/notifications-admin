from botocore.exceptions import ClientError as BotoClientError
from flask import current_app, redirect, render_template, request, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError

from app import letter_branding_client
from app.event_handlers import create_update_letter_branding_event
from app.main import main
from app.main.forms import (
    AdminEditLetterBrandingForm,
    AdminEditLetterBrandingSVGUploadForm,
    SearchByNameForm,
)
from app.models.branding import AllLetterBranding, LetterBranding
from app.s3_client.s3_logo_client import (
    LETTER_TEMP_TAG,
    delete_letter_temp_file,
    delete_letter_temp_files_created_by,
    letter_filename_for_db,
    permanent_letter_logo_name,
    persist_logo,
    upload_letter_temp_logo,
)
from app.utils.user import user_is_platform_admin


@main.route("/letter-branding", methods=["GET"])
@user_is_platform_admin
def letter_branding():
    return render_template(
        "views/letter-branding/select-letter-branding.html",
        letter_brandings=AllLetterBranding(),
        search_form=SearchByNameForm(),
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
@main.route("/letter-branding/<uuid:branding_id>/edit/<path:logo>", methods=["GET", "POST"])
@user_is_platform_admin
def update_letter_branding(branding_id, logo=None):
    letter_branding = LetterBranding.from_id(branding_id)

    file_upload_form = AdminEditLetterBrandingSVGUploadForm()
    letter_branding_details_form = AdminEditLetterBrandingForm(
        name=letter_branding.name,
    )

    file_upload_form_submitted = file_upload_form.file.data
    details_form_submitted = request.form.get("operation") == "branding-details"

    logo = logo or permanent_letter_logo_name(letter_branding.filename, "svg")

    if file_upload_form_submitted and file_upload_form.validate_on_submit():
        upload_filename = upload_letter_temp_logo(
            file_upload_form.file.data.filename,
            file_upload_form.file.data,
            current_app.config["AWS_REGION"],
            user_id=current_user.id,
        )

        if logo.startswith(LETTER_TEMP_TAG.format(user_id=current_user.id)):
            delete_letter_temp_file(logo)

        return redirect(url_for(".update_letter_branding", branding_id=branding_id, logo=upload_filename))

    if details_form_submitted and letter_branding_details_form.validate_on_submit():
        db_filename = letter_filename_for_db(logo, current_user.id)

        try:
            # If a new file has been uploaded, db_filename and letter_branding.filename will be different
            if db_filename != letter_branding.filename:
                upload_letter_svg_logo(logo, db_filename, current_user.id)

            letter_branding_client.update_letter_branding(
                branding_id=branding_id,
                filename=db_filename,
                name=letter_branding_details_form.name.data,
                updated_by_id=current_user.id,
            )
            create_update_letter_branding_event(
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
        logo=logo,
        is_update=True,
    )


@main.route("/letter-branding/create", methods=["GET", "POST"])
@main.route("/letter-branding/create/<path:logo>", methods=["GET", "POST"])
@user_is_platform_admin
def create_letter_branding(logo=None):
    file_upload_form = AdminEditLetterBrandingSVGUploadForm()
    letter_branding_details_form = AdminEditLetterBrandingForm()

    file_upload_form_submitted = file_upload_form.file.data
    details_form_submitted = request.form.get("operation") == "branding-details"

    if file_upload_form_submitted and file_upload_form.validate_on_submit():
        upload_filename = upload_letter_temp_logo(
            file_upload_form.file.data.filename,
            file_upload_form.file.data,
            current_app.config["AWS_REGION"],
            user_id=current_user.id,
        )

        if logo and logo.startswith(LETTER_TEMP_TAG.format(user_id=current_user.id)):
            delete_letter_temp_file(logo)

        return redirect(url_for(".create_letter_branding", logo=upload_filename))

    if details_form_submitted and letter_branding_details_form.validate_on_submit():
        if logo:
            db_filename = letter_filename_for_db(logo, current_user.id)

            try:
                letter_branding = LetterBranding.create(
                    filename=db_filename, name=letter_branding_details_form.name.data
                )

                upload_letter_svg_logo(logo, db_filename, current_user.id)

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
        logo=logo,
    )


def upload_letter_svg_logo(old_filename, new_filename, user_id):
    persist_logo(old_filename, permanent_letter_logo_name(new_filename, "svg"))

    delete_letter_temp_files_created_by(user_id)
