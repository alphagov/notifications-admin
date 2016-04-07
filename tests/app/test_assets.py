import app


def test_crown_logo(app_):
    with app_.test_request_context():
        #  This image is used by the email templates, so we should be really careful to make
        #  sure that its always there.
        response = app_.test_client().get('/static/images/email-template/crown-32px.gif')
    assert response.status_code == 200
