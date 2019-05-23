from flask import url_for
from lxml import html

from tests import user_json


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
    document = client_request.post('main.find_users_by_email', _data={"search": ""}, _expected_status=400)

    expected_message = "You need to enter full or partial email address to search by."
    assert document.find('span', {'class': 'error-message'}).text.strip() == expected_message


def test_user_information_page_shows_information_about_user(
    client,
    platform_admin_user,
    mocker
):
    mocker.patch('app.user_api_client.get_user', side_effect=[
        platform_admin_user,
        user_json(name="Apple Bloom", services=[1, 2])
    ], autospec=True)

    mocker.patch(
        'app.user_api_client.get_organisations_and_services_for_user',
        return_value={'organisations': [], 'services_without_organisations': [
            {"id": 1, "name": "Fresh Orchard Juice"},
            {"id": 2, "name": "Nature Therapy"},
        ]},
        autospec=True
    )
    client.login(platform_admin_user)
    response = client.get(url_for('main.user_information', user_id=345))
    assert response.status_code == 200

    document = html.fromstring(response.get_data(as_text=True))

    assert document.xpath("//h1/text()[normalize-space()='Apple Bloom']")
    assert document.xpath("//p/text()[normalize-space()='test@gov.uk']")
    assert document.xpath("//p/text()[normalize-space()='+447700900986']")

    assert document.xpath("//h2/text()[normalize-space()='Services']")
    assert document.xpath("//a/text()[normalize-space()='Fresh Orchard Juice']")
    assert document.xpath("//a/text()[normalize-space()='Nature Therapy']")

    assert document.xpath("//h2/text()[normalize-space()='Last login']")
    assert not document.xpath("//p/text()[normalize-space()='0 failed login attempts']")


def test_user_information_page_displays_if_there_are_failed_login_attempts(
    client,
    platform_admin_user,
    mocker
):
    mocker.patch('app.user_api_client.get_user', side_effect=[
        platform_admin_user,
        user_json(name="Apple Bloom", failed_login_count=2)
    ], autospec=True)

    mocker.patch(
        'app.user_api_client.get_organisations_and_services_for_user',
        return_value={'organisations': [], 'services_without_organisations': [
            {"id": 1, "name": "Fresh Orchard Juice"},
            {"id": 2, "name": "Nature Therapy"},
        ]},
        autospec=True
    )
    client.login(platform_admin_user)
    response = client.get(url_for('main.user_information', user_id=345))
    assert response.status_code == 200

    document = html.fromstring(response.get_data(as_text=True))
    assert document.xpath("//p/text()[normalize-space()='2 failed login attempts']")
