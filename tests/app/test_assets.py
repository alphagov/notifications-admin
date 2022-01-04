def test_crown_logo(client_request):
    #  This image is used by the email templates, so we should be really careful to make
    #  sure that its always there.
    client_request.logout()
    client_request.get_response_from_url(
        '/static/images/email-template/crown-32px.gif',
        _expected_status=200,
    )


def test_static_404s_return(client_request):
    client_request.get_response_from_url(
        '/static/images/some-image-that-doesnt-exist.png',
        _expected_status=404,
    )
