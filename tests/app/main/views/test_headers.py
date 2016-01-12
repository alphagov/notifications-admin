
def test_owasp_useful_headers_set(notifications_admin):
    with notifications_admin.test_request_context():
        response = notifications_admin.test_client().get('/')
    assert response.status_code == 200
    assert response.headers['X-Frame-Options'] == 'deny'
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-XSS-Protection'] == '1; mode=block'
    assert response.headers['Content-Security-Policy'] == "default-src 'self' 'unsafe-inline'"  # noqa
