from app.main.dao import services_dao
from app.main.forms import AddServiceForm
from tests.app.main import create_test_user


def test_form_should_have_errors_when_duplicate_service_is_added(notifications_admin,
                                                                 notifications_admin_db,
                                                                 notify_db_session):
    with notifications_admin.test_request_context(method='POST',
                                                  data={'service_name': 'some service'}) as req:
        user = create_test_user('active')
        services_dao.insert_new_service('some service', user)
        req.session['user_id'] = user.id
        form = AddServiceForm(req.request.form)
        assert form.validate() is False
        assert len(form.errors) == 1
        expected = {'service_name': ['Duplicate service name']}
        assert form.errors == expected
