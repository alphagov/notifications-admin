from flask import render_template, send_file
from flask_login import login_required

from app.main import main
from app.main.s3_client import get_mou
from app.main.views.sub_navigation_dictionaries import features_nav
from app.utils import AgreementInfo


@main.route('/agreement')
@login_required
def agreement():
    return render_template(
        'views/agreement.html',
        crown_status=AgreementInfo.from_current_user().crown_status_or_404,
        navigation_links=features_nav(),
    )


@main.route('/agreement.pdf')
@login_required
def download_agreement():
    return send_file(**get_mou(
        AgreementInfo.from_current_user().crown_status_or_404
    ))
