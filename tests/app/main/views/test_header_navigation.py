import pytest
from flask import url_for

from tests.conftest import normalize_spaces


@pytest.mark.parametrize(
    "signed_in, platform_admin, expected_navigation_items",
    (
        (
            False,
            False,
            (
                ("Support", ".support"),
                ("Features", ".guidance_features"),
                ("Pricing", ".guidance_pricing"),
                ("Using Notify", ".guidance_using_notify"),
                ("Sign in", ".sign_in"),
            ),
        ),
        (
            True,
            False,
            (
                ("Support", ".support"),
                ("Features", ".guidance_features"),
                ("Pricing", ".guidance_pricing"),
                ("Using Notify", ".guidance_using_notify"),
                ("Your account", ".user_profile"),
            ),
        ),
        (
            True,
            True,
            (
                ("Support", ".support"),
                ("Features", ".guidance_features"),
                ("Pricing", ".guidance_pricing"),
                ("Using Notify", ".guidance_using_notify"),
                ("Platform admin", ".platform_admin_search"),
                ("Your account", ".user_profile"),
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
        for link in page.select(".govuk-header__navigation-list .govuk-header__navigation-item a")
    ] == [(label, url_for(endpoint)) for label, endpoint in expected_navigation_items]
