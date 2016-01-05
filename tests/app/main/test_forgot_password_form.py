from werkzeug.datastructures import MultiDict

from app.main.forms import ForgotPasswordForm


def test_should_return_validation_error_if_email_address_does_not_exist(notifications_admin,
                                                                        notifications_admin_db,
                                                                        notify_db_session):
    with notifications_admin.test_request_context():
        form = ForgotPasswordForm(['first@it.gov.uk', 'second@it.gov.uk'],
                                  formdata=MultiDict([('email_address', 'not_found@it.gov.uk')]))
        form.validate()
        assert {'email_address': ['Please enter the email address that you registered with']} == form.errors
