from app.main.forms import AddServiceForm
from werkzeug.datastructures import MultiDict


def test_form_should_have_errors_when_duplicate_service_is_added(app_,
                                                                 db_,
                                                                 db_session):
    def _get_form_names():
        return ['some service', 'more names']
    with app_.test_request_context():
        form = AddServiceForm(_get_form_names,
                              formdata=MultiDict([('service_name', 'some service')]))
        form.validate()
        assert {'service_name': ['Service name already exists']} == form.errors
