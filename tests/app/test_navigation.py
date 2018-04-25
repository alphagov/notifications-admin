import pytest
from tests.conftest import SERVICE_ONE_ID, app_

from app.navigation import MainNavigation

all_endpoints = [
    rule.endpoint for rule in next(app_(None)).url_map.iter_rules()
]


def test_navigation_items_are_properly_defined():
    for endpoint in MainNavigation().endpoints_with_navigation:
        assert endpoint in all_endpoints
        assert endpoint not in MainNavigation().endpoints_without_navigation
        assert MainNavigation().endpoints_with_navigation.count(endpoint) == 1


def test_excluded_navigation_items_are_properly_defined():
    for endpoint in MainNavigation().endpoints_without_navigation:
        assert endpoint in all_endpoints
        assert endpoint not in MainNavigation().endpoints_with_navigation
        assert MainNavigation().endpoints_without_navigation.count(endpoint) == 1


def test_all_endpoints_are_covered():
    for endpoint in all_endpoints:
        assert endpoint in (
            MainNavigation().endpoints_with_navigation +
            MainNavigation().endpoints_without_navigation
        )


@pytest.mark.xfail(raises=KeyError)
def test_raises_on_invalid_navigation_item(client_request):
    MainNavigation().is_selected('foo')


@pytest.mark.parametrize('endpoint, selected_nav_item', [
    ('main.choose_template', 'Templates'),
    ('main.manage_users', 'Team members'),
])
def test_a_page_should_nave_selected_navigation_item(
    client_request,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    endpoint,
    selected_nav_item,
):
    page = client_request.get(endpoint, service_id=SERVICE_ONE_ID)
    selected_nav_items = page.select('.navigation a.selected')
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item
