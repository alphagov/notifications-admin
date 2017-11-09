def test_owasp_useful_headers_set(client, mocker):
    mocker.patch('app.get_cdn_domain', return_value='static-logos.test.com')

    response = client.get('/')

    assert response.status_code == 200
    assert response.headers['X-Frame-Options'] == 'deny'
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-XSS-Protection'] == '1; mode=block'
    assert response.headers['Content-Security-Policy'] == (
        "default-src 'self' 'unsafe-inline';"
        "script-src 'self' *.google-analytics.com 'unsafe-inline' 'unsafe-eval' data:;"
        "connect-src 'self' *.google-analytics.com;"
        "object-src 'self';"
        "font-src 'self' data:;"
        "img-src 'self' *.google-analytics.com *.notifications.service.gov.uk static-logos.test.com data:;"
        "frame-src www.youtube.com;"
    )
