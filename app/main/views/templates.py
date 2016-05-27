import string

from flask import request, render_template, redirect, url_for, flash, abort, session
from flask_login import login_required

from notifications_utils.template import Template, TemplateChange
from notifications_utils.recipients import first_column_heading
from notifications_python_client.errors import HTTPError

from app.main import main
from app.utils import user_has_permissions
from app.main.forms import SMSTemplateForm, EmailTemplateForm
from app.main.views.send import get_example_csv_rows
from app import service_api_client, current_service


form_objects = {
    'email': EmailTemplateForm,
    'sms': SMSTemplateForm
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
        template=Template(
            service_api_client.get_service_template(service_id, template_id)['data'],
            prefix=current_service['name']
        )
    )


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
        template=Template(
            service_api_client.get_service_template(service_id, template_id, version)['data'],
            prefix=current_service['name']
        )
    )


@main.route("/services/<service_id>/templates/add-<template_type>", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates', admin_override=True)
def add_service_template(service_id, template_type):
    if template_type not in ['sms', 'email']:
        abort(404)

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
        subject = form.subject.data if getattr(form, 'subject', None) else None
        new_template = Template({
            'name': form.name.data,
            'content': form.template_content.data,
            'subject': subject,
            'template_type': template['template_type'],
            'id': template['id']
        })
        template_change = Template(template).compare_to(new_template)
        if template_change.has_different_placeholders and not request.form.get('confirm'):
            return render_template(
                'views/templates/breaking-change.html',
                template_change=template_change,
                new_template=new_template,
                column_headings=list(string.ascii_uppercase[:len(new_template.placeholders) + 1]),
                example_rows=[
                    [first_column_heading[new_template.template_type]] + list(new_template.placeholders),
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
                '.choose_template',
                service_id=service_id,
                template_type=template['template_type']
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
    flash('Are you sure you want to delete ‘{}’?'.format(form.name.data), 'delete')
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
        template=Template(
            service_api_client.get_service_template(service_id, template_id)['data'],
            prefix=current_service['name']
        ),
        versions=[
            Template(
                template,
                prefix=current_service['name']
            ) for template in service_api_client.get_service_template_versions(service_id, template_id)['data']
        ]
    )
