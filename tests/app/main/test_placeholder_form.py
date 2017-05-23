from app.main.forms import get_placeholder_form_instance
from wtforms import Label


def test_form_class_not_mutated(app_):

    with app_.test_request_context(
        method='POST',
        data={'placeholder_value': ''}
    ) as req:
        form1 = get_placeholder_form_instance('name', {}, optional_placeholder=False)
        form2 = get_placeholder_form_instance('city', {}, optional_placeholder=True)

        assert not form1.validate_on_submit()
        assert form2.validate_on_submit()

        assert str(form1.placeholder_value.label) == '<label for="placeholder_value">name</label>'
        assert str(form2.placeholder_value.label) == '<label for="placeholder_value">city</label>'
