import pytest

from werkzeug.datastructures import MultiDict

from app.main.forms import CreateKeyForm


def test_return_validation_error_when_key_name_exists(app_):
    def _get_names():
        return ['some key', 'another key']

    with app_.test_request_context():
        form = CreateKeyForm(_get_names(),
                             formdata=MultiDict([('key_name', 'Some key')]))
        form.key_type.choices = [('a', 'a'), ('b', 'b')]
        form.validate()
        assert form.errors['key_name'] == ['A key with this name already exists']


@pytest.mark.parametrize(
    'key_type, expected_error', [
        ('', 'This field is required.'),
        ('invalid', 'Not a valid choice')
    ]
)
def test_return_validation_error_when_key_type_not_chosen(app_, key_type, expected_error):

    with app_.test_request_context():
        form = CreateKeyForm(
            [],
            formdata=MultiDict([('key_name', 'Some key'), ('key_type', key_type)]))
        form.key_type.choices = [('a', 'a'), ('b', 'b')]
        form.validate()
        assert form.errors['key_type'] == [expected_error]
