from flask import abort, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.main import main
from app.main.views.sub_navigation_dictionaries import features_nav
from app.s3_client.s3_mou_client import get_mou


@main.route('/agreement')
@login_required
def agreement():
    return render_template(
        'views/{}.html'.format(current_user.default_organisation.as_jinja_template),
        owner=current_user.default_organisation.name,
        navigation_links=features_nav(),
    )


@main.route('/agreement.pdf')
@login_required
def download_agreement():
    return send_file(**get_mou(
        current_user.default_organisation.crown_status_or_404
    ))


@main.route('/agreement/<variant>', endpoint='public_agreement')
@main.route('/agreement/<variant>.pdf', endpoint='public_download_agreement')
def public_agreement(variant):

    if variant not in {'crown', 'non-crown'}:
        abort(404)

    if request.endpoint == 'main.public_download_agreement':
        return send_file(**get_mou(
            organisation_is_crown=(variant == 'crown')
        ))

    return render_template(
        'views/agreement-public.html',
        owner=current_user.default_organisation.name,
        download_link=url_for('.public_download_agreement', variant=variant),
    )
