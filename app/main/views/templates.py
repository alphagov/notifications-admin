from flask import request, render_template, redirect, url_for
from flask_login import login_required

from app.main import main
from app.main.forms import TemplateForm


@main.route("/services/<int:service_id>/templates")
@login_required
def manage_templates(service_id):
    return render_template(
        'views/manage-templates.html',
        service_id=service_id
    )


@main.route("/services/<int:service_id>/templates/template", methods=['GET', 'POST'])
@login_required
def add_template(service_id):

    form = TemplateForm()

    form.template_name.data = 'Reminder'
    form.template_body.data = 'Vehicle tax: Your vehicle tax for ((registration number)) expires on ((date)). Tax your vehicle at www.gov.uk/vehicle-tax'  # noqa

    if request.method == 'GET':
        return render_template(
            'views/edit-template.html',
            h1='Edit template',
            form=form,
            service_id=service_id
        )
    elif request.method == 'POST':
        return redirect(url_for('.manage_templates', service_id=service_id))


@main.route("/services/<int:service_id>/templates/template/add", methods=['GET', 'POST'])
@login_required
def edit_template(service_id):

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
