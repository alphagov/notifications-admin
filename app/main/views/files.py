import random
from flask import redirect, request, render_template, url_for
from flask_login import login_required
from datetime import datetime, timedelta

from app import current_service
from app.main import main
from app.main.forms import BatchOptionsForm, PageCountForm, PDFUploadForm, PDFAndWordUploadForm
from app.utils import user_has_permissions


ADDRESSES = [
    'Megan Priest, Studio 11, Hall Manors, Burton-on-Trent, BT51 3NQS',
    'Olivia Stetler, 1 Green Terrace, Westmoreland, CT14 7EW',
    'Allan Hugo, 12a Russell Lock, Lewiston, WF1 5HR',
    'Valeria Fernández, 3rd floor, Caxton House, Tothill Street, London, SW1A 1WP',
    'Hank Scorpio, Managing Director, Globex, 2 Longacre, London, WC2A 4DF',
    'Jakayla Fitzpatrick, 51 Prospect Road, Portstewart, Coleraine, Northern Ireland, United Kingdom, BT557NG',
    'Madeleine Yang, 4 Johnson Orchard, North Aarlburgh, SP6 1NH',
    'Patrick Lance Sloan, 38, Rapide Way, Weston-super-Mare, North Somerset, BS24 8ER',
    'Joe Parry, 73 Netherpark Cres., Steel Cross, TN6 4WT',
    'Chloë Turner, Flat 2, 18 Admiral Drive, Stevenage, Hertfordshire, SG1 4QA',
]


def _get_batch_heading():
    return 'Uploaded letters – {}'.format(
        datetime.utcnow().strftime('%-d %B')
    )


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

    files_dict = {
        'file{}'.format(i): request.args.get('file{}'.format(i))
        for i in range(10)
    }

    return render_template(
        'views/files/new-batch.html',
        files=files,
        manage_link=url_for('.new_batch_manage', service_id=current_service.id, **files_dict),
        heading=_get_batch_heading(),
        time_now=datetime.utcnow().strftime('%-I:%M%p').lower(),
        edd=(datetime.utcnow() + timedelta(days=3)).strftime('%-d %B'),
        done=bool(request.args.get('done')),
        addresses=ADDRESSES,
    )


@main.route("/services/<service_id>/files/new-batch/manage", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def new_batch_manage(service_id):

    files_dict = {
        'file{}'.format(i): request.args.get('file{}'.format(i))
        for i in range(10)
    }

    form = BatchOptionsForm(name=_get_batch_heading())

    return render_template(
        'views/files/new-batch-manage.html',
        form=form,
        back_link=url_for('.new_batch', service_id=current_service.id, **files_dict),
        heading=_get_batch_heading(),
    )


@main.route("/services/<service_id>/files/one")
@login_required
@user_has_permissions()
def batch_one_file(service_id):

    return render_template(
        'views/files/batch-one-file.html',
        filename=request.args.get('filename'),
        time_now=datetime.utcnow().strftime('%-I:%M%p').lower(),
        edd=(datetime.utcnow() + timedelta(days=3)).strftime('%-d %B'),
    )


@main.route("/services/<service_id>/files/send-one")
@login_required
@user_has_permissions()
def batch_send_one_file(service_id):

    return render_template(
        'views/files/send-one-file.html',
        filename=request.args.get('filename'),
        done=bool(request.args.get('done')),
        time_now=datetime.utcnow().strftime('%-I:%M%p').lower(),
        edd=(datetime.utcnow() + timedelta(days=3)).strftime('%-d %B'),
        recipient=random.choice(ADDRESSES),
    )


@main.route("/services/<service_id>/files/new-batch-one", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def import_letters(service_id):

    form = PDFAndWordUploadForm()

    if form.validate_on_submit():
        filenames = form.file.data.filename.split(', ')
        if len(filenames) == 1:
            file = filenames[0]
            if file.lower().endswith('mrg.docx'):
                return redirect(url_for(
                    'main.new_batch',
                    service_id=current_service.id,
                    **{
                        'file{}'.format(index): '{} ({} of 10)'.format(file, index)
                        for index in range(1, 11)
                    }
                ))
            return redirect(url_for(
                'main.batch_send_one_file',
                service_id=current_service.id,
                filename=filenames[0],
            ))
        return redirect(url_for(
            'main.new_batch',
            service_id=current_service.id,
            **{
                'file{}'.format(index): filename
                for index, filename in enumerate(filenames)
            }
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
