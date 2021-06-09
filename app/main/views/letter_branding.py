from botocore.exceptions import ClientError as BotoClientError
from flask import (
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from notifications_python_client.errors import HTTPError

from app import letter_branding_client
from app.main import main
from app.main.forms import (
    SearchByNameForm,
    ServiceLetterBrandingDetails,
    SVGFileUpload,
)
from app.s3_client.s3_logo_client import (
    LETTER_TEMP_TAG,
    delete_letter_temp_file,
    delete_letter_temp_files_created_by,
    letter_filename_for_db,
    permanent_letter_logo_name,
    persist_logo,
    upload_letter_temp_logo,
)
from app.utils import get_logo_cdn_domain
from app.utils.user import user_is_platform_admin


@main.route("/letter-branding", methods=['GET'])
@user_is_platform_admin
def letter_branding():

    brandings = letter_branding_client.get_all_letter_branding()

    return render_template(
        'views/letter-branding/select-letter-branding.html',
        letter_brandings=brandings,
        search_form=SearchByNameForm()
    )


@main.route("/letter-branding/<uuid:branding_id>/edit", methods=['GET', 'POST'])
@main.route("/letter-branding/<uuid:branding_id>/edit/<path:logo>", methods=['GET', 'POST'])
@user_is_platform_admin
def update_letter_branding(branding_id, logo=None):
    letter_branding = letter_branding_client.get_letter_branding(branding_id)

    file_upload_form = SVGFileUpload()
    letter_branding_details_form = ServiceLetterBrandingDetails(
        name=letter_branding['name'],
    )

    file_upload_form_submitted = file_upload_form.file.data
    details_form_submitted = request.form.get('operation') == 'branding-details'

    logo = logo if logo else permanent_letter_logo_name(letter_branding['filename'], 'svg')

    if file_upload_form_submitted and file_upload_form.validate_on_submit():
        upload_filename = upload_letter_temp_logo(
            file_upload_form.file.data.filename,
            file_upload_form.file.data,
            current_app.config['AWS_REGION'],
            user_id=session["user_id"]
        )

        if logo.startswith(LETTER_TEMP_TAG.format(user_id=session['user_id'])):
            delete_letter_temp_file(logo)

        return redirect(url_for('.update_letter_branding', branding_id=branding_id, logo=upload_filename))

    if details_form_submitted and letter_branding_details_form.validate_on_submit():
        db_filename = letter_filename_for_db(logo, session['user_id'])

        try:
            if db_filename == letter_branding['filename']:

                letter_branding_client.update_letter_branding(
                    branding_id=branding_id,
                    filename=db_filename,
                    name=letter_branding_details_form.name.data,
                )

                return redirect(url_for('main.letter_branding'))
            else:
                letter_branding_client.update_letter_branding(
                    branding_id=branding_id,
                    filename=db_filename,
                    name=letter_branding_details_form.name.data,
                )

                upload_letter_svg_logo(logo, db_filename, session['user_id'])

                return redirect(url_for('main.letter_branding'))

        except HTTPError as e:
            if 'name' in e.message:
                letter_branding_details_form.name.errors.append(e.message['name'][0])
            else:
                raise e
        except BotoClientError:
            # we had a problem saving the file - rollback the db changes
            letter_branding_client.update_letter_branding(
                branding_id=branding_id,
                filename=letter_branding['filename'],
                name=letter_branding['name'],
            )
            file_upload_form.file.errors = ['Error saving uploaded file - try uploading again']

    return render_template(
        'views/letter-branding/manage-letter-branding.html',
        file_upload_form=file_upload_form,
        letter_branding_details_form=letter_branding_details_form,
        cdn_url=get_logo_cdn_domain(),
        logo=logo,
        is_update=True
    )


@main.route("/letter-branding/create", methods=['GET', 'POST'])
@main.route("/letter-branding/create/<path:logo>", methods=['GET', 'POST'])
@user_is_platform_admin
def create_letter_branding(logo=None):
    file_upload_form = SVGFileUpload()
    letter_branding_details_form = ServiceLetterBrandingDetails()

    file_upload_form_submitted = file_upload_form.file.data
    details_form_submitted = request.form.get('operation') == 'branding-details'

    if file_upload_form_submitted and file_upload_form.validate_on_submit():
        upload_filename = upload_letter_temp_logo(
            file_upload_form.file.data.filename,
            file_upload_form.file.data,
            current_app.config['AWS_REGION'],
            user_id=session["user_id"]
        )

        if logo and logo.startswith(LETTER_TEMP_TAG.format(user_id=session['user_id'])):
            delete_letter_temp_file(logo)

        return redirect(url_for('.create_letter_branding', logo=upload_filename))

    if details_form_submitted and letter_branding_details_form.validate_on_submit():
        if logo:
            db_filename = letter_filename_for_db(logo, session['user_id'])

            try:
                letter_branding_client.create_letter_branding(
                    filename=db_filename,
                    name=letter_branding_details_form.name.data,
                )

                upload_letter_svg_logo(logo, db_filename, session['user_id'])

                return redirect(url_for('main.letter_branding'))

            except HTTPError as e:
                if 'name' in e.message:
                    letter_branding_details_form.name.errors.append(e.message['name'][0])
                else:
                    raise e
        else:
            # Show error on upload form if trying to submit with no logo
            file_upload_form.validate()

    return render_template(
        'views/letter-branding/manage-letter-branding.html',
        file_upload_form=file_upload_form,
        letter_branding_details_form=letter_branding_details_form,
        cdn_url=get_logo_cdn_domain(),
        logo=logo
    )


def upload_letter_svg_logo(old_filename, new_filename, user_id):
    persist_logo(old_filename, permanent_letter_logo_name(new_filename, 'svg'))

    delete_letter_temp_files_created_by(user_id)
