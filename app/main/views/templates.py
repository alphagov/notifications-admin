from flask import request, render_template, redirect, url_for, flash, abort
from flask_login import login_required

from app.main import main
from app.main.forms import SMSTemplateForm, EmailTemplateForm
from app.main.dao import templates_dao as tdao
from app.main.dao import services_dao as sdao


form_objects = {
    'email': EmailTemplateForm,
    'sms': SMSTemplateForm
}


@main.route("/services/<service_id>/templates/add-<template_type>", methods=['GET', 'POST'])
@login_required
def add_service_template(service_id, template_type):

    service = sdao.get_service_by_id_or_404(service_id)

    if template_type not in ['sms', 'email']:
        abort(404)

    form = form_objects[template_type]()

    if form.validate_on_submit():
        tdao.insert_service_template(
            form.name.data,
            template_type,
            form.template_content.data,
            service_id,
            form.subject.data if hasattr(form, 'subject') else None
        )
        return redirect(
            url_for('.choose_template', service_id=service_id, template_type=template_type)
        )

    return render_template(
        'views/edit-{}-template.html'.format(template_type),
        form=form,
        template_type=template_type,
        service_id=service_id
    )


@main.route("/services/<service_id>/templates/<int:template_id>", methods=['GET', 'POST'])
@login_required
def edit_service_template(service_id, template_id):
    template = tdao.get_service_template_or_404(service_id, template_id)['data']
    template['template_content'] = template['content']
    form = form_objects[template['template_type']](**template)

    if form.validate_on_submit():
        tdao.update_service_template(
            template_id, form.name.data, template['template_type'],
            form.template_content.data, service_id
        )
        return redirect(url_for(
            '.choose_template',
            service_id=service_id,
            template_type=template['template_type']
        ))

    return render_template(
        'views/edit-{}-template.html'.format(template['template_type']),
        form=form,
        service_id=service_id,
        template_id=template_id,
        template_type=template['template_type']
    )


@main.route("/services/<service_id>/templates/<int:template_id>/delete", methods=['GET', 'POST'])
@login_required
def delete_service_template(service_id, template_id):
    template = tdao.get_service_template_or_404(service_id, template_id)['data']

    if request.method == 'POST':
        tdao.delete_service_template(service_id, template_id)
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
        service_id=service_id,
        template_id=template_id)
