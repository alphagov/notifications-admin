from flask import request, render_template, redirect, url_for

from app.main import main


@main.route("/templates")
def manage_templates():
    return render_template('views/manage-templates.html')


@main.route("/templates/template", methods=['GET', 'POST'])
def add_template():
    if request.method == 'GET':
        return render_template(
            'views/edit-template.html',
            template_name='Reminder',
            template_body='Vehicle tax: Your vehicle tax for ((registration number)) expires on ((date)). Tax your vehicle at www.gov.uk/vehicle-tax',  # noqa
            h1='Edit template'
        )
    elif request.method == 'POST':
        return redirect(url_for('.manage_templates'))


@main.route("/templates/template/add", methods=['GET', 'POST'])
def edit_template():
    if request.method == 'GET':
        return render_template(
            'views/edit-template.html',
            h1='Add template'
        )
    elif request.method == 'POST':
        return redirect(url_for('.manage_templates'))
