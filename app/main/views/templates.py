from datetime import datetime, timedelta
from string import ascii_uppercase

from flask import request, render_template, redirect, url_for, flash, abort, send_file
from flask_login import login_required
from flask_weasyprint import HTML, render_pdf
from dateutil.parser import parse

from notifications_utils.template import LetterPreviewTemplate
from notifications_utils.recipients import first_column_headings
from notifications_python_client.errors import HTTPError

from app.main import main
from app.utils import user_has_permissions, get_template, png_from_pdf
from app.main.forms import SMSTemplateForm, EmailTemplateForm, LetterTemplateForm
from app.main.views.send import get_example_csv_rows
from app import service_api_client, current_service, template_statistics_client


form_objects = {
    'email': EmailTemplateForm,
    'sms': SMSTemplateForm,
    'letter': LetterTemplateForm
}

page_headings = {
    'email': 'email',
    'sms': 'text message'
}


@main.route("/services/<service_id>/templates/<template_id>")
@login_required
@user_has_permissions(
    'view_activity',
    'send_texts',
    'send_emails',
    'manage_templates',
    'manage_api_keys',
    admin_override=True, any_=True
)
def view_template(service_id, template_id):
    return render_template(
        'views/templates/template.html',
        template=get_template(
            service_api_client.get_service_template(service_id, template_id)['data'],
            current_service,
            expand_emails=True,
            letter_preview_url=url_for('.view_template', service_id=service_id, template_id=template_id)
        )
    )


@main.route("/services/<service_id>/templates/<template_id>.pdf")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_letter_template_as_pdf(service_id, template_id):
    return render_pdf(HTML(string=str(
        LetterPreviewTemplate(
            service_api_client.get_service_template(service_id, template_id)['data'],
        )
    )))


@main.route("/services/<service_id>/templates/<template_id>.png")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_letter_template_as_png(service_id, template_id):
    return send_file(**png_from_pdf(
        view_letter_template_as_pdf(service_id, template_id)
    ))


def _view_template_version(service_id, template_id, version, letters_as_pdf=False):
    return dict(template=get_template(
        service_api_client.get_service_template(service_id, template_id, version=version)['data'],
        current_service,
        expand_emails=True,
        letter_preview_url=url_for(
            '.view_template_version',
            service_id=service_id,
            template_id=template_id,
            version=version,
        ) if not letters_as_pdf else None
    ))


@main.route("/services/<service_id>/templates/<template_id>/version/<int:version>")
@login_required
@user_has_permissions(
    'view_activity',
    'send_texts',
    'send_emails',
    'manage_templates',
    'manage_api_keys',
    admin_override=True,
    any_=True
)
def view_template_version(service_id, template_id, version):
    return render_template(
        'views/templates/template_history.html',
        **_view_template_version(service_id=service_id, template_id=template_id, version=version)
    )


@main.route("/services/<service_id>/templates/<template_id>/version/<int:version>.pdf")
@login_required
@user_has_permissions(
    'view_activity',
    'send_texts',
    'send_emails',
    'manage_templates',
    'manage_api_keys',
    admin_override=True,
    any_=True
)
def view_template_version_as_pdf(service_id, template_id, version):
    return render_pdf(HTML(string=str(
        LetterPreviewTemplate(
            service_api_client.get_service_template(service_id, template_id, version=version)['data'],
        )
    )))


@main.route("/services/<service_id>/templates/<template_id>/version/<int:version>.png")
@login_required
@user_has_permissions(
    'view_activity',
    'send_texts',
    'send_emails',
    'manage_templates',
    'manage_api_keys',
    admin_override=True,
    any_=True
)
def view_template_version_as_png(service_id, template_id, version):
    return send_file(**png_from_pdf(
        view_template_version_as_pdf(service_id, template_id, version)
    ))


@main.route("/services/<service_id>/templates/add-<template_type>", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates', admin_override=True)
def add_service_template(service_id, template_type):
    if template_type not in ['sms', 'email', 'letter']:
        abort(404)
    if not current_service['can_send_letters'] and template_type == 'letter':
        abort(403)

    form = form_objects[template_type]()
    if form.validate_on_submit():
        try:
            service_api_client.create_service_template(
                form.name.data,
                template_type,
                form.template_content.data,
                service_id,
                form.subject.data if hasattr(form, 'subject') else None
            )
        except HTTPError as e:
            if e.status_code == 400:
                if 'content' in e.message and any(['character count greater than' in x for x in e.message['content']]):
                    form.template_content.errors.extend(e.message['content'])
                else:
                    raise e
            else:
                raise e
        else:
            return redirect(
                url_for('.choose_template', service_id=service_id, template_type=template_type)
            )

    return render_template(
        'views/edit-{}-template.html'.format(template_type),
        form=form,
        template_type=template_type,
        heading_action='Add'
    )


@main.route("/services/<service_id>/templates/<template_id>/edit", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates', admin_override=True)
def edit_service_template(service_id, template_id):
    template = service_api_client.get_service_template(service_id, template_id)['data']
    template['template_content'] = template['content']
    form = form_objects[template['template_type']](**template)

    if form.validate_on_submit():
        subject = form.subject.data if hasattr(form, 'subject') else None
        new_template = get_template({
            'name': form.name.data,
            'content': form.template_content.data,
            'subject': subject,
            'template_type': template['template_type'],
            'id': template['id']
        }, current_service)
        template_change = get_template(template, current_service).compare_to(new_template)
        if template_change.has_different_placeholders and not request.form.get('confirm'):
            return render_template(
                'views/templates/breaking-change.html',
                template_change=template_change,
                new_template={
                    'name': form.name.data,
                    'subject': subject,
                    'content': form.template_content.data,
                },
                column_headings=list(ascii_uppercase[:len(new_template.placeholders) + 1]),
                example_rows=[
                    first_column_headings[new_template.template_type] + list(new_template.placeholders),
                    get_example_csv_rows(new_template),
                    get_example_csv_rows(new_template)
                ],
                form=form
            )
        try:
            service_api_client.update_service_template(
                template_id,
                form.name.data,
                template['template_type'],
                form.template_content.data,
                service_id,
                subject
            )
        except HTTPError as e:
            if e.status_code == 400:
                if 'content' in e.message and any(['character count greater than' in x for x in e.message['content']]):
                    form.template_content.errors.extend(e.message['content'])
                else:
                    raise e
            else:
                raise e
        else:
            return redirect(url_for(
                '.view_template',
                service_id=service_id,
                template_id=template_id
            ))
    return render_template(
        'views/edit-{}-template.html'.format(template['template_type']),
        form=form,
        template_id=template_id,
        template_type=template['template_type'],
        heading_action='Edit'
    )


@main.route("/services/<service_id>/templates/<template_id>/delete", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates', admin_override=True)
def delete_service_template(service_id, template_id):
    template = service_api_client.get_service_template(service_id, template_id)['data']

    if request.method == 'POST':
        service_api_client.delete_service_template(service_id, template_id)
        return redirect(url_for(
            '.choose_template',
            service_id=service_id,
            template_type=template['template_type']
        ))

    template['template_content'] = template['content']
    form = form_objects[template['template_type']](**template)

    try:
        last_used_notification = template_statistics_client.get_template_statistics_for_template(
            service_id, template['id']
        )
        message = '{} was last used {} ago'.format(
            last_used_notification['template']['name'],
            get_human_readable_delta(
                parse(last_used_notification['created_at']).replace(tzinfo=None),
                datetime.utcnow())
        )
    except HTTPError as e:
        if e.status_code == 404:
            message = '{} has never been used'.format(template['name'])
        else:
            raise e

    flash('{}. Are you sure you want to delete it?'.format(message), 'delete')
    return render_template(
        'views/edit-{}-template.html'.format(template['template_type']),
        h1='Edit template',
        form=form,
        template_id=template_id)


@main.route('/services/<service_id>/templates/<template_id>/versions')
@login_required
@user_has_permissions(
    'view_activity',
    'send_texts',
    'send_emails',
    'manage_templates',
    'manage_api_keys',
    admin_override=True,
    any_=True
)
def view_template_versions(service_id, template_id):
    return render_template(
        'views/templates/choose_history.html',
        versions=[
            get_template(
                template,
                current_service,
                expand_emails=True,
                letter_preview_url=url_for(
                    '.view_template_version',
                    service_id=service_id,
                    template_id=template_id,
                    version=template['version'],
                )
            )
            for template in service_api_client.get_service_template_versions(service_id, template_id)['data']
        ]
    )


def get_last_use_message(template_name, template_statistics):
    try:
        most_recent_use = max(
            parse(template_stats['updated_at']).replace(tzinfo=None)
            for template_stats in template_statistics
        )
    except ValueError:
        return '{} has never been used'.format(template_name)

    return '{} was last used {} ago'.format(
        template_name,
        get_human_readable_delta(most_recent_use, datetime.utcnow())
    )


def get_human_readable_delta(from_time, until_time):
    delta = until_time - from_time
    if delta < timedelta(seconds=60):
        return 'under a minute'
    elif delta < timedelta(hours=1):
        minutes = int(delta.seconds / 60)
        return '{} minute{}'.format(minutes, '' if minutes == 1 else 's')
    elif delta < timedelta(days=1):
        hours = int(delta.seconds / 3600)
        return '{} hour{}'.format(hours, '' if hours == 1 else 's')
    else:
        days = delta.days
        return '{} day{}'.format(days, '' if days == 1 else 's')
