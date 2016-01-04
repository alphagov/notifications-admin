from app.main.forms import AddServiceForm
from werkzeug.datastructures import MultiDict


def test_form_should_have_errors_when_duplicate_service_is_added(notifications_admin,
                                                                 notifications_admin_db,
                                                                 notify_db_session):
    with notifications_admin.test_request_context():
        form = AddServiceForm(['some service', 'more names'],
                              formdata=MultiDict([('service_name', 'some service')]))
        form.validate()
        assert {'service_name': ['Service name already exists']} == form.errors
