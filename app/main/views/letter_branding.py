from flask import render_template, send_file
from flask_login import login_required

from app.main import main
from app.template_previews import get_letter_logo_file, get_letter_logos
from app.utils import user_is_platform_admin


@main.route("/letter-branding", methods=['GET'])
@login_required
@user_is_platform_admin
def letter_branding():
    return render_template(
        'views/letter-branding/letter-branding.html',
        logos=sorted(get_letter_logos().items()),
    )


@main.route("/letter-branding/<filename>", methods=['GET'])
@login_required
@user_is_platform_admin
def letter_branding_logo(filename):
    return send_file(
        get_letter_logo_file(filename),
        attachment_filename=filename
    )
