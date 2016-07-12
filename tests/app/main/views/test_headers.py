
def test_owasp_useful_headers_set(app_):
    with app_.test_request_context():
        response = app_.test_client().get('/')
    assert response.status_code == 200
    assert response.headers['X-Frame-Options'] == 'deny'
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-XSS-Protection'] == '1; mode=block'
    assert response.headers['Content-Security-Policy'] == (
        "default-src 'self' 'unsafe-inline';"
        "script-src 'self' *.google-analytics.com 'unsafe-inline' data:;"
        "object-src 'self';"
        "font-src 'self' data:;"
        "img-src 'self' *.google-analytics.com *.notifications.service.gov.uk data:;"
    )
