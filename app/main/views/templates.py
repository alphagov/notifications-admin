from flask import request, render_template, redirect, url_for
from flask_login import login_required

from app.main import main
from app.main.forms import TemplateForm


@main.route("/templates")
@login_required
def manage_templates():
    return render_template('views/manage-templates.html')


@main.route("/templates/template", methods=['GET', 'POST'])
@login_required
def add_template():

    form = TemplateForm()

    form.template_name.data = 'Reminder'
    form.template_body.data = 'Vehicle tax: Your vehicle tax for ((registration number)) expires on ((date)). Tax your vehicle at www.gov.uk/vehicle-tax'  # noqa

    if request.method == 'GET':
        return render_template(
            'views/edit-template.html',
            h1='Edit template',
            form=form
        )
    elif request.method == 'POST':
        return redirect(url_for('.manage_templates'))


@main.route("/templates/template/add", methods=['GET', 'POST'])
@login_required
def edit_template():

    form = TemplateForm()

    if request.method == 'GET':
        return render_template(
            'views/edit-template.html',
            h1='Add template',
            form=form
        )
    elif request.method == 'POST':
        return redirect(url_for('.manage_templates'))
