from datetime import datetime

from flask import abort, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app import current_service
from app.main import main
from app.main.forms import AcceptAgreementForm
from app.main.views.sub_navigation_dictionaries import features_nav
from app.s3_client.s3_mou_client import get_mou
from app.utils import user_has_permissions


@main.route('/agreement')
@login_required
def agreement():
    return render_template(
        'views/agreement/{}.html'.format(current_user.default_organisation.as_jinja_template),
        owner=current_user.default_organisation.name,
        navigation_links=features_nav(),
    )


@main.route('/services/<uuid:service_id>/agreement')
@user_has_permissions('manage_service')
@login_required
def service_agreement(service_id):
    return render_template(
        'views/agreement/service-{}.html'.format(current_service.organisation.as_jinja_template),
        owner=current_service.organisation.name,
    )


@main.route('/services/<uuid:service_id>/agreement.pdf')
@user_has_permissions('manage_service')
@login_required
def service_download_agreement(service_id):
    return send_file(**get_mou(
        current_service.organisation.crown_status_or_404
    ))


@main.route('/services/<uuid:service_id>/agreement/accept', methods=['GET', 'POST'])
@user_has_permissions('manage_service')
@login_required
def service_accept_agreement(service_id):

    if not current_service.organisation:
        abort(404)

    form = AcceptAgreementForm.from_organisation(current_service.organisation)

    if form.validate_on_submit():
        current_service.organisation.update(
            agreement_signed_version=float(form.version.data),
            agreement_signed_on_behalf_of_name=form.on_behalf_of_name.data,
            agreement_signed_on_behalf_of_email_address=form.on_behalf_of_email.data,
        )
        return redirect(url_for('main.service_confirm_agreement', service_id=current_service.id))

    return render_template(
        'views/agreement/agreement-accept.html',
        form=form,
    )


@main.route('/services/<uuid:service_id>/agreement/confirm', methods=['GET', 'POST'])
@user_has_permissions('manage_service')
@login_required
def service_confirm_agreement(service_id):

    if (
        not current_service.organisation
        or current_service.organisation.agreement_signed_version is None
    ):
        abort(403)

    if request.method == 'POST':
        current_service.organisation.update(
            agreement_signed=True,
            agreement_signed_at=str(datetime.utcnow()),
            agreement_signed_by_id=current_user.id,
        )
        return redirect(url_for('main.request_to_go_live', service_id=current_service.id))

    return render_template('views/agreement/agreement-confirm.html')


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
        'views/agreement/agreement-public.html',
        owner=current_user.default_organisation.name,
        download_link=url_for('.public_download_agreement', variant=variant),
    )
