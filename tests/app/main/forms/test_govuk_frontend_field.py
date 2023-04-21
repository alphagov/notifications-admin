from unittest.mock import ANY

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


def test_govuk_frontend_widget_mixin_calls_render(client_request, mocker):
    mock_render = mocker.patch(
        "app.utils.govuk_frontend_field.render_govuk_frontend_macro",
        return_value="my html",
        autospec=True,
    )

    class MyField(GovukFrontendWidgetMixin, StringField):
        govuk_frontend_component_name = "component"

    class MyForm(Form):
        field = MyField()

    my_form = MyForm()

    rendered_field = my_form.field()

    assert rendered_field == mock_render.return_value
    mock_render.assert_called_once_with("component", {})


def test_govuk_frontend_widget_mixin_takes_instance_params_over_class_params(client_request, mocker):
    mock_render = mocker.patch(
        "app.utils.govuk_frontend_field.render_govuk_frontend_macro",
        return_value="my html",
        autospec=True,
    )

    class MyField(GovukFrontendWidgetMixin, StringField):
        govuk_frontend_component_name = "component"
        param_extensions = {"foo": "bar"}

    class MyForm(Form):
        field = MyField(param_extensions={"foo": "baz"})

    MyForm().field()

    mock_render.assert_called_once_with(ANY, {"foo": "baz"})


def test_govuk_frontend_widget_mixin_takes_render_params_over_class_params(client_request, mocker):
    mock_render = mocker.patch(
        "app.utils.govuk_frontend_field.render_govuk_frontend_macro",
        return_value="my html",
        autospec=True,
    )

    class MyField(GovukFrontendWidgetMixin, StringField):
        govuk_frontend_component_name = "component"
        param_extensions = {"foo": "bar"}

    class MyForm(Form):
        field = MyField(param_extensions={"foo": "baz"})

    MyForm().field(param_extensions={"foo": "waz"})

    mock_render.assert_called_once_with(ANY, {"foo": "waz"})


def test_govuk_frontend_widget_mixin_constructs_errors(client_request):
    class MyField(GovukFrontendWidgetMixin, StringField):
        govuk_frontend_component_name = "component"

    class MyForm(Form):
        field = MyField("some-name")

    my_form = MyForm()
    my_form.field.errors = ["some error message"]

    ret = my_form.field.get_error_message(error_message_format="html")
    assert ret == {
        "attributes": {
            "data-error-label": "field",
            "data-error-type": "some error message",
            "data-notify-module": "track-error",
        },
        "html": "some error message",
    }
