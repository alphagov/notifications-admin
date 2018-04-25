import pytest
from tests.conftest import ORGANISATION_ID, SERVICE_ONE_ID, app_

from app.navigation import HeaderNavigation, MainNavigation, OrgNavigation

all_endpoints = [
    rule.endpoint for rule in next(app_(None)).url_map.iter_rules()
]


@pytest.mark.parametrize('navigation_instance', [
    MainNavigation(),
    HeaderNavigation(),
    OrgNavigation(),
])
def test_navigation_items_are_properly_defined(navigation_instance):
    for endpoint in navigation_instance.endpoints_with_navigation:
        assert (
            endpoint in all_endpoints
        ), '{} is not a real endpoint (in {}.mapping)'.format(
            endpoint,
            type(navigation_instance).__name__
        )
        assert (
            endpoint not in navigation_instance.endpoints_without_navigation
        ), '{} is listed in {}.mapping and {}.exclude'.format(
            endpoint,
            type(navigation_instance).__name__,
            type(navigation_instance).__name__,
        )
        assert (
            navigation_instance.endpoints_with_navigation.count(endpoint) == 1
        ), '{} found more than once in {}.mapping'.format(
            endpoint,
            type(navigation_instance).__name__
        )


@pytest.mark.parametrize('navigation_instance', [
    MainNavigation(),
    HeaderNavigation(),
    OrgNavigation(),
])
def test_excluded_navigation_items_are_properly_defined(navigation_instance):
    for endpoint in navigation_instance.endpoints_without_navigation:
        assert (
            endpoint in all_endpoints
        ), '{} is not a real endpoint (in {}.exclude)'.format(
            endpoint,
            type(navigation_instance).__name__
        )
        assert (
            endpoint not in navigation_instance.endpoints_with_navigation
        ), '{} is listed in {}.exclude and {}.mapping'.format(
            endpoint,
            type(navigation_instance).__name__,
            type(navigation_instance).__name__,
        )
        assert (
            navigation_instance.endpoints_without_navigation.count(endpoint) == 1
        ), '{} found more than once in {}.exclude'.format(
            endpoint,
            type(navigation_instance).__name__
        )


@pytest.mark.parametrize('navigation_instance', [
    MainNavigation(),
    HeaderNavigation(),
    OrgNavigation(),
])
def test_all_endpoints_are_covered(navigation_instance):
    for endpoint in all_endpoints:
        assert endpoint in (
            navigation_instance.endpoints_with_navigation +
            navigation_instance.endpoints_without_navigation
        ), '{} is not listed or excluded in {}'.format(
            endpoint,
            type(navigation_instance).__name__
        )


@pytest.mark.parametrize('navigation_instance', [
    MainNavigation(),
    HeaderNavigation(),
    OrgNavigation(),
])
@pytest.mark.xfail(raises=KeyError)
def test_raises_on_invalid_navigation_item(
    client_request, navigation_instance
):
    navigation_instance.is_selected('foo')


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


@pytest.mark.parametrize('endpoint, selected_nav_item', [
    ('main.documentation', 'Documentation'),
    ('main.support', 'Support'),
])
def test_a_page_should_nave_selected_header_navigation_item(
    client_request,
    endpoint,
    selected_nav_item,
):
    page = client_request.get(endpoint, service_id=SERVICE_ONE_ID)
    selected_nav_items = page.select('#proposition-links a.active')
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item


@pytest.mark.parametrize('endpoint, selected_nav_item', [
    ('main.organisation_dashboard', 'Dashboard'),
    ('main.manage_org_users', 'Team members'),
])
def test_a_page_should_nave_selected_org_navigation_item(
    client_request,
    mock_get_organisation,
    mock_get_organisation_services,
    mock_get_users_for_organisation,
    mock_get_invited_users_for_organisation,
    endpoint,
    selected_nav_item,
):
    page = client_request.get(endpoint, org_id=ORGANISATION_ID)
    selected_nav_items = page.select('.navigation a.selected')
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item
