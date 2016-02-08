from flask import request, render_template, redirect, url_for, flash, abort
from flask_login import login_required

from app.main import main
from app.main.forms import TemplateForm
from app import job_api_client
from app.main.dao.services_dao import get_service_by_id
from app.main.dao import templates_dao as tdao
from app.main.dao import services_dao as sdao
from client.errors import HTTPError


@main.route("/services/<service_id>/templates")
@login_required
def manage_service_templates(service_id):
    try:
        jobs = job_api_client.get_job(service_id)['data']
        templates = tdao.get_service_templates(service_id)['data']
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e
    return render_template(
        'views/manage-templates.html',
        service_id=service_id,
        has_jobs=bool(jobs),
        templates=[tdao.TemplatesBrowsableItem(x) for x in templates])


@main.route("/services/<service_id>/templates/add", methods=['GET', 'POST'])
@login_required
def add_service_template(service_id):
    try:
        service = sdao.get_service_by_id(service_id)['data']
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e

    form = TemplateForm()

    if form.validate_on_submit():
        tdao.insert_service_template(
            form.name.data, form.template_type.data, form.template_content.data, service_id)
        return redirect(url_for(
            '.manage_service_templates', service_id=service_id))
    return render_template(
        'views/edit-template.html',
        h1='Add template',
        form=form,
        service_id=service_id)


@main.route("/services/<service_id>/templates/<int:template_id>", methods=['GET', 'POST'])
@login_required
def edit_service_template(service_id, template_id):
    try:
        template = tdao.get_service_template(service_id, template_id)['data']
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e

    template['template_content'] = template['content']
    form = TemplateForm(**template)

    if form.validate_on_submit():
        tdao.update_service_template(
            template_id, form.name.data, form.template_type.data,
            form.template_content.data, service_id)
        return redirect(url_for('.manage_service_templates', service_id=service_id))

    return render_template(
        'views/edit-template.html',
        h1='Edit template',
        form=form,
        service_id=service_id,
        template_id=template_id)


@main.route("/services/<service_id>/templates/<int:template_id>/delete", methods=['GET', 'POST'])
@login_required
def delete_service_template(service_id, template_id):
    try:
        template = tdao.get_service_template(service_id, template_id)['data']
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e

    template['template_content'] = template['content']
    form = TemplateForm(**template)

    if request.method == 'POST':
        tdao.delete_service_template(service_id, template_id)
        return redirect(url_for('.manage_service_templates', service_id=service_id))

    flash('Are you sure you want to delete ‘{}’?'.format(form.name.data), 'delete')
    return render_template(
        'views/edit-template.html',
        h1='Edit template',
        form=form,
        service_id=service_id,
        template_id=template_id)
