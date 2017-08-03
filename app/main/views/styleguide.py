from flask import render_template, current_app, abort
from flask_wtf import FlaskForm as Form
from wtforms import StringField, PasswordField, TextAreaField, FileField, validators
from notifications_utils.template import Template
from app.main import main


@main.route('/_styleguide')
def styleguide():

    if not current_app.config['SHOW_STYLEGUIDE']:
        abort(404)

    class FormExamples(Form):
        username = StringField(u'Username')
        password = PasswordField(u'Password', [validators.required()])
        code = StringField('Enter code')
        message = TextAreaField(u'Message')
        file_upload = FileField('Upload a CSV file to add your recipients’ details')

    sms = "Your vehicle tax for ((registration number)) is due on ((date)). Renew online at www.gov.uk/vehicle-tax"

    form = FormExamples()
    form.message.data = sms
    form.validate()

    template = Template({'content': sms})

    return render_template(
        'views/styleguide.html',
        form=form,
        template=template
    )
