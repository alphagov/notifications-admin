from flask_wtf import FlaskForm as Form
from wtforms import StringField

from app.utils.govuk_frontend_field import GovukFrontendWidgetMixin


def test_govuk_frontend_widget_mixin_separates_params_properly(client_request):
    class MyField(GovukFrontendWidgetMixin, StringField):
        govuk_frontend_component_name = "foo"

    class FormOne(Form):
        field = MyField("label1", param_extensions={"foo": "bar"})

    class FormTwo(Form):
        field = MyField("label2", param_extensions={"baz": "waz"})

    form1 = FormOne()
    form2 = FormTwo()
    assert form1.field.param_extensions == {"foo": "bar"}
    assert form2.field.param_extensions == {"baz": "waz"}
