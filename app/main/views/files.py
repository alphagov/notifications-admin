from flask import redirect, render_template, url_for
from flask_login import current_user, login_required

from app import current_service
from app.main import main
from app.main.forms import NewBatchForm
from app.utils import user_has_permissions


@main.route("/services/<service_id>/files")
@login_required
@user_has_permissions()
def files(service_id):
    return render_template(
        'views/files/index.html',
    )


@main.route("/services/<service_id>/files/new-contact-list")
@login_required
@user_has_permissions()
def new_contact_list(service_id):
    return render_template(
        'views/files/new-contact-list.html',
    )


@main.route("/services/<service_id>/files/new-batch", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def new_batch(service_id):

    return render_template(
        'views/files/new-batch.html'
    )


@main.route("/services/<service_id>/files/new-batch-one", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def import_letters(service_id):

    return render_template(
        'views/files/new-batch-import.html'
    )


@main.route("/services/<service_id>/files/new-batch-many-chunk", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def import_letters_collated_chunk(service_id):

    return render_template(
        'views/files/new-batch-import-collated-chunk.html'
    )


@main.route("/services/<service_id>/files/new-batch-many", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def import_letters_collated(service_id):

    return render_template(
        'views/files/new-batch-import-collated.html'
    )
