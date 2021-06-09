from datetime import datetime

from flask import abort, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from app import current_service
from app.main import main
from app.main.forms import AcceptAgreementForm
from app.models.organisation import Organisation
from app.s3_client.s3_mou_client import get_mou
from app.utils.user import user_has_permissions


@main.route('/services/<uuid:service_id>/agreement')
@user_has_permissions('manage_service')
def service_agreement(service_id):
    if not current_service.organisation:
        if current_service.organisation_type == Organisation.TYPE_NHS_GP:
            return redirect(
                url_for('main.add_organisation_from_gp_service', service_id=current_service.id)
            )
        if current_service.organisation_type == Organisation.TYPE_NHS_LOCAL:
            return redirect(
                url_for('main.add_organisation_from_nhs_local_service', service_id=current_service.id)
            )
    if current_service.organisation.crown is None:
        return render_template('views/agreement/service-agreement-choose.html')
    if current_service.organisation.agreement_signed:
        return render_template('views/agreement/service-agreement-signed.html')
    return render_template('views/agreement/service-agreement.html')


@main.route('/services/<uuid:service_id>/agreement.pdf')
@user_has_permissions('manage_service')
def service_download_agreement(service_id):
    return send_file(**get_mou(
        current_service.organisation.crown_status_or_404
    ))


@main.route('/services/<uuid:service_id>/agreement/accept', methods=['GET', 'POST'])
@user_has_permissions('manage_service')
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
