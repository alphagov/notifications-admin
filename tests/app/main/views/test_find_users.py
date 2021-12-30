import uuid

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from lxml import html
from notifications_python_client.errors import HTTPError

from tests import user_json
from tests.conftest import normalize_spaces


def test_find_users_by_email_page_loads_correctly(client_request, platform_admin_user):
    client_request.login(platform_admin_user)
    document = client_request.get('main.find_users_by_email')

    assert document.h1.text.strip() == 'Find users by email'
    assert len(document.find_all('input', {'type': 'search'})) > 0


def test_find_users_by_email_displays_users_found(
    client_request,
    platform_admin_user,
    mocker
):
    client_request.login(platform_admin_user)
    mocker.patch(
        'app.user_api_client.find_users_by_full_or_partial_email',
        return_value={"data": [user_json()]},
        autospec=True,
    )
    document = client_request.post(
        'main.find_users_by_email',
        _data={"search": "twilight.sparkle"},
        _expected_status=200
    )

    assert any(element.text.strip() == 'test@gov.uk' for element in document.find_all(
        'a', {'class': 'browse-list-link'}, href=True)
    )
    assert any(element.text.strip() == 'Test User' for element in document.find_all('p', {'class': 'browse-list-hint'}))

    assert document.find('a', {'class': 'browse-list-link'}).text.strip() == 'test@gov.uk'
    assert document.find('p', {'class': 'browse-list-hint'}).text.strip() == 'Test User'


def test_find_users_by_email_displays_multiple_users(
    client_request,
    platform_admin_user,
    mocker
):
    client_request.login(platform_admin_user)
    mocker.patch(
        'app.user_api_client.find_users_by_full_or_partial_email',
        return_value={"data": [user_json(name="Apple Jack"), user_json(name="Apple Bloom")]},
        autospec=True,
    )
    document = client_request.post('main.find_users_by_email', _data={"search": "apple"}, _expected_status=200)

    assert any(
        element.text.strip() == 'Apple Jack' for element in document.find_all('p', {'class': 'browse-list-hint'})
    )
    assert any(
        element.text.strip() == 'Apple Bloom' for element in document.find_all('p', {'class': 'browse-list-hint'})
    )


def test_find_users_by_email_displays_message_if_no_users_found(
    client_request,
    platform_admin_user,
    mocker
):
    client_request.login(platform_admin_user)
    mocker.patch('app.user_api_client.find_users_by_full_or_partial_email', return_value={"data": []}, autospec=True)
    document = client_request.post(
        'main.find_users_by_email', _data={"search": "twilight.sparkle"}, _expected_status=200
    )

    assert document.find('p', {'class': 'browse-list-hint'}).text.strip() == 'No users found.'


def test_find_users_by_email_validates_against_empty_search_submission(
    client_request,
    platform_admin_user,
    mocker
):
    client_request.login(platform_admin_user)
    document = client_request.post('main.find_users_by_email', _data={"search": ""}, _expected_status=200)

    expected_message = "Error: You need to enter full or partial email address to search by."
    assert document.find('span', {'class': 'govuk-error-message'}).text.strip() == expected_message


def test_user_information_page_shows_information_about_user(
    client,
    platform_admin_user,
    mocker,
    fake_uuid,
):
    user_service_one = uuid.uuid4()
    user_service_two = uuid.uuid4()
    mocker.patch('app.user_api_client.get_user', side_effect=[
        platform_admin_user,
        user_json(name="Apple Bloom", services=[user_service_one, user_service_two])
    ], autospec=True)

    mocker.patch(
        'app.user_api_client.get_organisations_and_services_for_user',
        return_value={'organisations': [], 'services': [
            {"id": user_service_one, "name": "Fresh Orchard Juice", "restricted": True},
            {"id": user_service_two, "name": "Nature Therapy", "restricted": False},
        ]},
        autospec=True
    )
    client.login(platform_admin_user)
    response = client.get(url_for('main.user_information', user_id=fake_uuid))
    assert response.status_code == 200

    document = html.fromstring(response.get_data(as_text=True))

    assert document.xpath("//h1/text()[normalize-space()='Apple Bloom']")
    assert document.xpath("//p/text()[normalize-space()='test@gov.uk']")
    assert document.xpath("//p/text()[normalize-space()='+447700900986']")

    assert document.xpath("//h2/text()[normalize-space()='Live services']")
    assert document.xpath("//a/text()[normalize-space()='Nature Therapy']")

    assert document.xpath("//h2/text()[normalize-space()='Trial mode services']")
    assert document.xpath("//a/text()[normalize-space()='Fresh Orchard Juice']")

    assert document.xpath("//h2/text()[normalize-space()='Last login']")
    assert not document.xpath("//p/text()[normalize-space()='0 failed login attempts']")


def test_user_information_page_displays_if_there_are_failed_login_attempts(
    client,
    platform_admin_user,
    mocker,
    fake_uuid,
):
    mocker.patch('app.user_api_client.get_user', side_effect=[
        platform_admin_user,
        user_json(name="Apple Bloom", failed_login_count=2)
    ], autospec=True)

    mocker.patch(
        'app.user_api_client.get_organisations_and_services_for_user',
        return_value={'organisations': [], 'services': []},
        autospec=True
    )
    client.login(platform_admin_user)
    response = client.get(url_for('main.user_information', user_id=fake_uuid))
    assert response.status_code == 200

    document = html.fromstring(response.get_data(as_text=True))
    assert document.xpath("//p/text()[normalize-space()='2 failed login attempts']")


def test_user_information_page_shows_archive_link_for_active_users(
    client_request,
    platform_admin_user,
    api_user_active,
    mock_get_organisations_and_services_for_user,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        'main.user_information', user_id=api_user_active['id']
    )
    archive_url = url_for('main.archive_user', user_id=api_user_active['id'])

    link = page.find('a', {'href': archive_url})
    assert normalize_spaces(link.text) == 'Archive user'


def test_user_information_page_does_not_show_archive_link_for_inactive_users(
    mocker,
    client,
    platform_admin_user,
    mock_get_organisations_and_services_for_user,
):
    inactive_user = user_json(state='inactive')
    mocker.patch('app.user_api_client.get_user', side_effect=[platform_admin_user, inactive_user], autospec=True)
    client.login(platform_admin_user)
    response = client.get(
        url_for('main.user_information', user_id=inactive_user['id'])
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    archive_url = url_for('main.archive_user', user_id=inactive_user['id'])
    assert not page.find('a', {'href': archive_url})


def test_archive_user_prompts_for_confirmation(
    client_request,
    platform_admin_user,
    api_user_active,
    mock_get_organisations_and_services_for_user,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        'main.archive_user', user_id=api_user_active['id']
    )

    assert 'Are you sure you want to archive this user?' in page.find('div', class_='banner-dangerous').text


def test_archive_user_posts_to_user_client(
    client_request,
    platform_admin_user,
    api_user_active,
    mocker,
    mock_events,
):
    mock_user_client = mocker.patch('app.user_api_client.post')

    client_request.login(platform_admin_user)
    client_request.post(
        'main.archive_user', user_id=api_user_active['id'],
        _expected_redirect=url_for(
            'main.user_information',
            user_id=api_user_active['id'],
            _external=True,
        ),
    )

    mock_user_client.assert_called_once_with('/user/{}/archive'.format(api_user_active['id']), data=None)

    assert mock_events.called


def test_archive_user_shows_error_message_if_user_cannot_be_archived(
    client_request,
    platform_admin_user,
    api_user_active,
    mocker,
    mock_get_non_empty_organisations_and_services_for_user,
):
    mocker.patch(
        'app.user_api_client.post',
        side_effect=HTTPError(
            response=mocker.Mock(
                status_code=400,
                json={'result': 'error',
                      'message': 'User can’t be removed from a service - check all services have another '
                      'team member with manage_settings'}
            ),
            message='User can’t be removed from a service - check all services have another team member '
            'with manage_settings'
        )
    )

    client_request.login(platform_admin_user)
    page = client_request.post(
        'main.archive_user',
        user_id=api_user_active['id'],
        _follow_redirects=True,
    )

    assert normalize_spaces(page.find('h1').text) == 'Platform admin user'
    assert normalize_spaces(
        page.select_one('.banner-dangerous').text
    ) == 'User can’t be removed from a service - check all services have another team member with manage_settings'


def test_archive_user_does_not_create_event_if_user_client_raises_unexpected_exception(
    client_request,
    platform_admin_user,
    api_user_active,
    mocker,
    mock_events,
):
    with pytest.raises(Exception):
        client_request.login(platform_admin_user)
        client_request.post(
            'main.archive_user', user_id=api_user_active.id,
        )

    assert not mock_events.called
