from flask import request, render_template, redirect, url_for, flash
from flask_login import login_required

from app.main import main
from app.main.forms import TemplateForm

from ._templates import templates


@main.route("/services/<int:service_id>/templates")
@login_required
def manage_templates(service_id):
    return render_template(
        'views/manage-templates.html',
        service_id=service_id,
        templates=templates,
    )


@main.route("/services/<int:service_id>/templates/add", methods=['GET', 'POST'])
@login_required
def add_template(service_id):

    form = TemplateForm()

    if request.method == 'GET':
        return render_template(
            'views/edit-template.html',
            h1='Add template',
            form=form,
            service_id=service_id
        )
    elif request.method == 'POST':
        return redirect(url_for('.manage_templates', service_id=service_id))


@main.route("/services/<int:service_id>/templates/<int:template_id>", methods=['GET', 'POST'])
@login_required
def edit_template(service_id, template_id):

    form = TemplateForm()

    form.template_name.data = templates[template_id - 1]['name']
    form.template_body.data = templates[template_id - 1]['body']

    if request.method == 'GET':
        return render_template(
            'views/edit-template.html',
            h1='Edit template',
            form=form,
            service_id=service_id,
            template_id=template_id
        )
    elif request.method == 'POST':
        return redirect(url_for('.manage_templates', service_id=service_id))


@main.route("/services/<int:service_id>/templates/<int:template_id>/delete", methods=['GET', 'POST'])
@login_required
def delete_template(service_id, template_id):

    form = TemplateForm()

    form.template_name.data = templates[template_id - 1]['name']
    form.template_body.data = templates[template_id - 1]['body']

    if request.method == 'GET':

        flash('Are you sure you want to delete ‘{}’?'.format(form.template_name.data), 'delete')

        return render_template(
            'views/edit-template.html',
            h1='Edit template',
            form=form,
            service_id=service_id,
            template_id=template_id
        )
    elif request.method == 'POST':
        if request.form.get('delete'):
            return redirect(url_for('.manage_templates', service_id=service_id))
        else:
            return redirect(url_for('.manage_templates', service_id=service_id))
