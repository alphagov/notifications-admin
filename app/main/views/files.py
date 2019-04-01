from flask import redirect, request, render_template, url_for
from flask_login import current_user, login_required

from app import current_service
from app.main import main
from app.main.forms import NewBatchForm, PageCountForm, PDFUploadForm
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

    files = list(filter(None, (
        request.args.get('file{}'.format(i))
        for i in range(10)
    )))

    return render_template(
        'views/files/new-batch.html',
        files=files,
    )


@main.route("/services/<service_id>/files/one")
@login_required
@user_has_permissions()
def batch_one_file(service_id):

    return render_template(
        'views/files/batch-one-file.html',
        filename=request.args.get('filename'),
    )


@main.route("/services/<service_id>/files/new-batch-one", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def import_letters(service_id):

    form = PDFUploadForm()

    if form.validate_on_submit():
        files = {
            'file{}'.format(index): filename
            for index, filename in enumerate(form.file.data.filename.split(', '))
        }
        return redirect(url_for(
            'main.new_batch',
            service_id=current_service.id,
            **files
        ))

    return render_template(
        'views/files/new-batch-import.html',
        form=form,
    )


@main.route("/services/<service_id>/files/new-batch-many-chunk", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def import_letters_collated_chunk(service_id):

    form = PageCountForm()

    if form.validate_on_submit():
        return redirect(url_for(
            '.import_letters_collated',
            service_id=current_service.id,
            page_count=form.page_count.data,
        ))

    return render_template(
        'views/files/new-batch-import-collated-chunk.html',
        form=form,
    )


@main.route("/services/<service_id>/files/new-batch-many", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def import_letters_collated(service_id):

    form = PDFUploadForm()

    if form.validate_on_submit():
        files = {
            'file{}'.format(index): '{} – {} of 10'.format(form.file.data.filename, index + 1)
            for index in range(10)
        }
        return redirect(url_for(
            'main.new_batch',
            service_id=current_service.id,
            **files
        ))

    return render_template(
        'views/files/new-batch-import-collated.html',
        form=form,
        page_count=request.args.get('page_count')
    )
