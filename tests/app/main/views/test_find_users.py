import uuid

import pytest
from flask import url_for
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
    client_request,
    platform_admin_user,
    mocker,
    fake_uuid,
):
    client_request.login(platform_admin_user)
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
    page = client_request.get('main.user_information', user_id=fake_uuid)

    assert normalize_spaces(page.select_one('h1').text) == 'Apple Bloom'

    assert [
        normalize_spaces(p.text) for p in page.select('main p')
    ] == [
        'test@gov.uk',
        '+447700900986',
        'Text message code',
        'Last logged in just now',
    ]

    assert '0 failed login attempts' not in page.text

    assert [
        normalize_spaces(h2.text) for h2 in page.select('main h2')
    ] == [
        'Live services',
        'Trial mode services',
        'Authentication',
        'Last login',
    ]

    assert [
        normalize_spaces(a.text) for a in page.select('main li a')
    ] == [
        'Nature Therapy',
        'Fresh Orchard Juice',
    ]


def test_user_information_page_shows_change_auth_type_link(
    client_request,
    platform_admin_user,
    api_user_active,
    mock_get_organisations_and_services_for_user,
    mocker
):
    client_request.login(platform_admin_user)
    mocker.patch('app.user_api_client.get_user', side_effect=[
        platform_admin_user,
        user_json(id_=api_user_active['id'], name="Apple Bloom", auth_type='sms_auth')
    ], autospec=True)

    page = client_request.get(
        'main.user_information', user_id=api_user_active['id']
    )
    change_auth_url = url_for('main.change_user_auth', user_id=api_user_active['id'])

    link = page.find('a', {'href': change_auth_url})
    assert normalize_spaces(link.text) == 'Change authentication for this user'


def test_user_information_page_doesnt_show_change_auth_type_link_if_user_on_webauthn(
    client_request,
    platform_admin_user,
    api_user_active,
    mock_get_organisations_and_services_for_user,
    mocker
):
    client_request.login(platform_admin_user)
    mocker.patch('app.user_api_client.get_user', side_effect=[
        platform_admin_user,
        user_json(id_=api_user_active['id'], name="Apple Bloom", auth_type='webauthn_auth')
    ], autospec=True)

    page = client_request.get(
        'main.user_information', user_id=api_user_active['id']
    )
    change_auth_url = url_for('main.change_user_auth', user_id=api_user_active['id'])

    link = page.find_all('a', {'href': change_auth_url})
    assert len(link) == 0


@pytest.mark.parametrize('current_auth_type', ['email_auth', 'sms_auth'])
def test_change_user_auth_preselects_current_auth_type(
    client_request,
    platform_admin_user,
    api_user_active,
    mocker,
    current_auth_type
):
    client_request.login(platform_admin_user)

    mocker.patch('app.user_api_client.get_user', side_effect=[
        platform_admin_user,
        user_json(id_=api_user_active['id'], name="Apple Bloom", auth_type=current_auth_type)
    ], autospec=True)

    checked_radios = client_request.get(
        'main.change_user_auth',
        user_id=api_user_active['id'],
    ).select(
        '.govuk-radios__item input[checked]'
    )

    assert len(checked_radios) == 1
    assert checked_radios[0]['value'] == current_auth_type


def test_change_user_auth(
    client_request,
    platform_admin_user,
    api_user_active,
    mocker
):

    client_request.login(platform_admin_user)

    mocker.patch('app.user_api_client.get_user', side_effect=[
        platform_admin_user,
        user_json(id_=api_user_active['id'], name="Apple Bloom", auth_type='sms_auth')
    ], autospec=True)

    mock_update = mocker.patch('app.user_api_client.update_user_attribute')

    client_request.post(
        'main.change_user_auth',
        user_id=api_user_active['id'],
        _data={
            'auth_type': 'email_auth'
        },
        _expected_redirect=url_for('main.user_information', user_id=api_user_active['id'])
    )

    mock_update.assert_called_once_with(
        api_user_active['id'],
        auth_type='email_auth',
    )


def test_user_information_page_displays_if_there_are_failed_login_attempts(
    client_request,
    platform_admin_user,
    mocker,
    fake_uuid,
):
    client_request.login(platform_admin_user)
    mocker.patch('app.user_api_client.get_user', side_effect=[
        platform_admin_user,
        user_json(name="Apple Bloom", failed_login_count=2)
    ], autospec=True)

    mocker.patch(
        'app.user_api_client.get_organisations_and_services_for_user',
        return_value={'organisations': [], 'services': []},
        autospec=True
    )
    page = client_request.get('main.user_information', user_id=fake_uuid)

    assert normalize_spaces(page.select('main p')[-1].text) == (
        '2 failed login attempts'
    )


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
    client_request,
    platform_admin_user,
    mock_get_organisations_and_services_for_user,
):
    inactive_user_id = uuid.uuid4()
    inactive_user = user_json(id_=inactive_user_id, state='inactive')
    client_request.login(platform_admin_user)
    mocker.patch('app.user_api_client.get_user', side_effect=[platform_admin_user, inactive_user], autospec=True)

    page = client_request.get(
        'main.user_information', user_id=inactive_user_id
    )

    archive_url = url_for('main.archive_user', user_id=inactive_user_id)
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
