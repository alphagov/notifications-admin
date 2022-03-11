import pytest
from wtforms import Form, StringField

from app.main.forms import StripWhitespaceForm, StripWhitespaceStringField


class ExampleForm(StripWhitespaceForm):
    foo = StringField('Foo')


class ExampleFormSpecialField(Form):
    foo = StripWhitespaceStringField('foo')


@pytest.mark.parametrize('submitted_data', [
    'bar',
    ' bar ',
    """
        \t    bar
    """,
    ' \u180E\u200B \u200C bar \u200D \u2060\uFEFF ',
])
@pytest.mark.parametrize('form', [
    ExampleForm,
    ExampleFormSpecialField,
])
def test_form_strips_all_whitespace(
    notify_admin,
    form,
    submitted_data,
):
    assert form(foo=submitted_data).foo.data == 'bar'
