from werkzeug.datastructures import MultiDict

from app.main.forms import CreateKeyForm


def test_return_validation_error_when_key_name_exists(app_,
                                                      db_,
                                                      db_session):
    def _get_names():
        return ['some key', 'another key']

    with app_.test_request_context():
        form = CreateKeyForm(_get_names(),
                             formdata=MultiDict([('key_name', 'some key')]))
        form.validate()
        assert {'key_name': ['A key with this name already exists']} == form.errors
