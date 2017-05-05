def test_crown_logo(client):
    #  This image is used by the email templates, so we should be really careful to make
    #  sure that its always there.
    response = client.get('/static/images/email-template/crown-32px.gif')
    assert response.status_code == 200


def test_static_404s_return(client):
    response = client.get('/static/images/some-image-that-doesnt-exist.png')
    assert response.status_code == 404
