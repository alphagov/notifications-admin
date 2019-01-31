from flask import (
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import login_required
from requests import get as requests_get

from app import letter_branding_client
from app.main import main
from app.main.forms import ServiceLetterBrandingDetails, SVGFileUpload
from app.s3_client.s3_logo_client import (
    LETTER_TEMP_TAG,
    delete_letter_temp_file,
    delete_letter_temp_files_created_by,
    get_letter_filename_with_no_path_or_extension,
    letter_filename_for_db,
    permanent_letter_logo_name,
    persist_logo,
    upload_letter_png_logo,
    upload_letter_temp_logo,
)
from app.utils import get_logo_cdn_domain, user_is_platform_admin


@main.route("/letter-branding/create", methods=['GET', 'POST'])
@main.route("/letter-branding/create/<path:logo>", methods=['GET', 'POST'])
@login_required
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

            letter_branding_client.create_letter_branding(
                filename=db_filename,
                name=letter_branding_details_form.name.data,
                domain=letter_branding_details_form.domain.data,
            )

            png_file = get_png_file_from_svg(logo)

            persist_logo(logo, permanent_letter_logo_name(db_filename, 'svg'))

            upload_letter_png_logo(
                permanent_letter_logo_name(db_filename, 'png'),
                png_file,
                current_app.config['AWS_REGION'],
            )

            delete_letter_temp_files_created_by(session['user_id'])

            # TODO: redirect to all letter branding page once it exists
            return redirect(url_for('main.platform_admin'))

        # Show error on upload form if trying to submit with no logo
        file_upload_form.validate()

    return render_template(
        'views/letter-branding/manage-letter-branding.html',
        file_upload_form=file_upload_form,
        letter_branding_details_form=letter_branding_details_form,
        cdn_url=get_logo_cdn_domain(),
        logo=logo
    )


def get_png_file_from_svg(filename):
    filename_for_template_preview = get_letter_filename_with_no_path_or_extension(filename)

    template_preview_svg_endpoint = '{}/{}.svg.png'.format(
        current_app.config['TEMPLATE_PREVIEW_API_HOST'],
        filename_for_template_preview
    )

    response = requests_get(
        template_preview_svg_endpoint,
        headers={'Authorization': 'Token {}'.format(current_app.config['TEMPLATE_PREVIEW_API_KEY'])}
    )

    return response.content
