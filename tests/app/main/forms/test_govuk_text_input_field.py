from flask_wtf import FlaskForm as Form

from app.main.forms import GovukTextInputField


def test_GovukTextInputField_renders_zero(client_request):
    class FakeForm(Form):
        field = GovukTextInputField()

    form = FakeForm(field=0)
    html = form.field()
    assert 'value="0"' in html
