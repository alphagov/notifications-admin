import pytest
from flask import url_for

from tests.conftest import normalize_spaces


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "signed_in, platform_admin, expected_navigation_items",
    (
        (
            False,
            False,
            (
                ("Features", ".guidance_features"),
                ("Pricing", ".guidance_pricing"),
                ("Using Notify", ".guidance_using_notify"),
                ("Support", ".support"),
                ("Sign in", ".sign_in"),
            ),
        ),
        (
            True,
            False,
            (
                ("Your services", ".your_services"),
                ("Features", ".guidance_features"),
                ("Pricing", ".guidance_pricing"),
                ("Using Notify", ".guidance_using_notify"),
                ("Support", ".support"),
                ("Your account", ".your_account"),
            ),
        ),
        (
            True,
            True,
            (
                ("Your services", ".your_services"),
                ("Features", ".guidance_features"),
                ("Pricing", ".guidance_pricing"),
                ("Using Notify", ".guidance_using_notify"),
                ("Support", ".support"),
                ("Platform admin", ".platform_admin_search"),
                ("Your account", ".your_account"),
            ),
        ),
    ),
)
def test_header_navigation(
    client_request,
    signed_in,
    platform_admin,
    expected_navigation_items,
    active_user_with_permissions,
):
    active_user_with_permissions["platform_admin"] = platform_admin
    client_request.login(active_user_with_permissions)
    if not signed_in:
        client_request.logout()
    page = client_request.get("main.guidance_features")
    assert [
        (normalize_spaces(link.text), link["href"])
        for link in page.select(".govuk-service-navigation__list .govuk-service-navigation__item a")
    ] == [(label, url_for(endpoint)) for label, endpoint in expected_navigation_items]
