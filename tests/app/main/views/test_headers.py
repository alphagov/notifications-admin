def test_owasp_useful_headers_set(
    client_request,
    mocker,
    mock_get_service_and_organisation_counts,
    mock_get_letter_rates,
    mock_get_sms_rate,
    fake_nonce,
):
    mocker.patch("secrets.token_urlsafe", return_value=fake_nonce)

    client_request.logout()
    response = client_request.get_response(".index")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["X-Permitted-Cross-Domain-Policies"] == "none"
    assert response.headers["Content-Security-Policy"] == (
        "default-src 'self' static.example.com 'unsafe-inline';"
        "script-src 'self' static.example.com 'nonce-TESTs5Vr8v3jgRYLoQuVwA';"
        "connect-src 'self' static.example.com;"
        "object-src 'self';"
        "font-src 'self' static.example.com data:;"
        "img-src "
        "'self' static.example.com"
        " *.notifications.service.gov.uk static-logos.test.com data:;"
        "style-src 'self' static.example.com 'unsafe-inline';"
        "frame-ancestors 'self';"
        "frame-src 'self';"
    )
    assert response.headers["Link"] == (
        "<https://static.example.com>; rel=dns-prefetch, <https://static.example.com>; rel=preconnect"
    )
    assert response.headers["Cache-Control"] == "no-store, no-cache, private, must-revalidate"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains; preload"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Cross-Origin-Embedder-Policy"] == "require-corp static.example.com;"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin static.example.com;"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin static.example.com;"
    assert (
        response.headers["Permissions-Policy"]
        == "geolocation=(), microphone=(), camera=(), autoplay=(), payment=(), sync-xhr=()"
    )
    assert response.headers["Server"] == "Cloudfront"


def test_headers_non_ascii_characters_are_replaced(
    client_request,
    mocker,
    mock_get_service_and_organisation_counts,
    mock_get_letter_rates,
    mock_get_sms_rate,
    fake_nonce,
):
    mocker.patch("secrets.token_urlsafe", return_value=fake_nonce)

    client_request.logout()
    mocker.patch.dict(
        "app.current_app.config",
        values={"LOGO_CDN_DOMAIN": "static-logos€æ.test.com"},
    )

    response = client_request.get_response(".index")

    assert response.headers["Content-Security-Policy"] == (
        "default-src 'self' static.example.com 'unsafe-inline';"
        "script-src 'self' static.example.com 'nonce-TESTs5Vr8v3jgRYLoQuVwA';"
        "connect-src 'self' static.example.com;"
        "object-src 'self';"
        "font-src 'self' static.example.com data:;"
        "img-src"
        " 'self' static.example.com"
        " *.notifications.service.gov.uk static-logos??.test.com data:;"
        "style-src 'self' static.example.com 'unsafe-inline';"
        "frame-ancestors 'self';"
        "frame-src 'self';"
    )
