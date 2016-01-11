from flask import render_template
from flask_wtf import Form
from wtforms import StringField, PasswordField, TextAreaField, validators
from app.main import main


@main.route('/_styleguide')
def styleguide():

    class FormExamples(Form):
        username = StringField(u'Username')
        password = PasswordField(u'Password', [validators.required()])
        message = TextAreaField(u'Message')

    form = FormExamples()

    form.message.data = "Your vehicle tax for ((registration number)) is due on ((date)). Renew online at www.gov.uk/vehicle-tax"  # noqa

    form.validate()

    return render_template(
        'views/styleguide.html',
        form=form
    )
