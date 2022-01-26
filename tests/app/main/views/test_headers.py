

def test_owasp_useful_headers_set(
    client_request,
    mocker,
    mock_get_service_and_organisation_counts,
):
    client_request.logout()
    response = client_request.get_response('.index')

    assert response.headers['X-Frame-Options'] == 'deny'
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-XSS-Protection'] == '1; mode=block'
    assert response.headers['Content-Security-Policy'] == (
        "default-src 'self' static.example.com 'unsafe-inline';"
        "script-src 'self' static.example.com *.google-analytics.com 'unsafe-inline' 'unsafe-eval' data:;"
        "connect-src 'self' *.google-analytics.com;"
        "object-src 'self';"
        "font-src 'self' static.example.com data:;"
        "img-src "
        "'self' static.example.com *.tile.openstreetmap.org *.google-analytics.com"
        " *.notifications.service.gov.uk static-logos.test.com data:;"
        "frame-src 'self' www.youtube-nocookie.com;"
    )
    assert response.headers['Link'] == (
        '<https://static.example.com>; rel=dns-prefetch, '
        '<https://static.example.com>; rel=preconnect'
    )


def test_headers_non_ascii_characters_are_replaced(
    client_request,
    mocker,
    mock_get_service_and_organisation_counts,
):
    client_request.logout()
    mocker.patch.dict(
        'app.current_app.config',
        values={'LOGO_CDN_DOMAIN': 'static-logos€æ.test.com'},
    )

    response = client_request.get_response('.index')

    assert response.headers['Content-Security-Policy'] == (
        "default-src 'self' static.example.com 'unsafe-inline';"
        "script-src 'self' static.example.com *.google-analytics.com 'unsafe-inline' 'unsafe-eval' data:;"
        "connect-src 'self' *.google-analytics.com;"
        "object-src 'self';"
        "font-src 'self' static.example.com data:;"
        "img-src"
        " 'self' static.example.com *.tile.openstreetmap.org *.google-analytics.com"
        " *.notifications.service.gov.uk static-logos??.test.com data:;"
        "frame-src 'self' www.youtube-nocookie.com;"
    )
