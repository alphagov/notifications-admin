import pytest


@pytest.mark.parametrize('url', [
    '/security.txt',
    '/.well-known/security.txt',
])
def test_security_policy_redirects_to_policy(client_request, url):
    client_request.get_url(
        url,
        _expected_status=302,
        _expected_redirect="https://vdp.cabinetoffice.gov.uk/.well-known/security.txt",
    )
