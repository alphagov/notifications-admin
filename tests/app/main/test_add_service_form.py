from app.main.forms import AddServiceForm
from werkzeug.datastructures import MultiDict


def test_form_should_have_errors_when_duplicate_service_is_added(app_):
    def _get_form_names():
        return ['some service', 'more names']
    with app_.test_request_context():
        form = AddServiceForm(_get_form_names,
                              formdata=MultiDict([('name', 'some service')]))
        form.validate()
        assert {'name': ['Service name already exists']} == form.errors
