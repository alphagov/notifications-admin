from flask import url_for
from lxml import html

from app.notify_client.user_api_client import User
from tests import user_json
from tests.conftest import mock_get_user


def test_find_users_by_email_page_loads_correctly(
    client,
    platform_admin_user,
    mocker
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for('main.find_users_by_email'))
    assert response.status_code == 200

    document = html.fromstring(response.get_data(as_text=True))
    assert document.xpath("//h1/text()[normalize-space()='Find users by email']")
    assert len(document.xpath("//input[@type='search']")) > 0


def test_find_users_by_email_displays_users_found(
    client,
    platform_admin_user,
    mocker
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    mocker.patch(
        'app.user_api_client.find_users_by_full_or_partial_email',
        return_value={"data": [user_json()]},
        autospec=True,
    )
    response = client.post(url_for('main.find_users_by_email'), data={"search": "twilight.sparkle"})
    assert response.status_code == 200

    document = html.fromstring(response.get_data(as_text=True))
    assert document.xpath("//a/text()[normalize-space()='test@gov.uk']")
    assert document.xpath("//p/text()[normalize-space()='Test User']")


def test_find_users_by_email_displays_multiple_users(
    client,
    platform_admin_user,
    mocker
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    mocker.patch('app.user_api_client.find_users_by_full_or_partial_email', return_value={"data": [
        user_json(name="Apple Jack"),
        user_json(name="Apple Bloom")
    ]}, autospec=True)
    response = client.post(url_for('main.find_users_by_email'), data={"search": "apple"})
    assert response.status_code == 200

    document = html.fromstring(response.get_data(as_text=True))

    assert document.xpath("//p/text()[normalize-space()='Apple Jack']")
    assert document.xpath("//p/text()[normalize-space()='Apple Bloom']")


def test_find_users_by_email_displays_message_if_no_users_found(
    client,
    platform_admin_user,
    mocker
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    mocker.patch('app.user_api_client.find_users_by_full_or_partial_email', return_value={"data": []}, autospec=True)
    response = client.post(url_for('main.find_users_by_email'), data={"search": "twilight.sparkle"})
    assert response.status_code == 200

    document = html.fromstring(response.get_data(as_text=True))
    assert document.xpath("//p/text()[normalize-space()='No users found.']")


def test_find_users_by_email_validates_against_empty_search_submission(
    client,
    platform_admin_user,
    mocker
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.post(url_for('main.find_users_by_email'), data={"search": ""})
    assert response.status_code == 400

    document = html.fromstring(response.get_data(as_text=True))
    expected_message = "You need to enter full or partial email address to search by."
    assert document.xpath(
        "//span[contains(@class, 'error-message') and normalize-space(text()) = '{}']".format(expected_message)
    )


def test_user_information_page_shows_information_about_user(
    client,
    platform_admin_user,
    mocker
):
    mocker.patch('app.user_api_client.get_user', side_effect=[
        platform_admin_user,
        User(user_json(name="Apple Bloom", services=[
            {"id": 1, "name": "Fresh Orchard Juice"},
            {"id": 2, "name": "Nature Therapy"},
        ]))
    ], autospec=True)
    client.login(platform_admin_user)
    response = client.get(url_for('main.user_information', user_id=345))
    assert response.status_code == 200

    document = html.fromstring(response.get_data(as_text=True))

    assert document.xpath("//h1/text()[normalize-space()='Apple Bloom']")
    assert document.xpath("//p/text()[normalize-space()='test@gov.uk']")
    assert document.xpath("//p/text()[normalize-space()='+447700900986']")

    assert document.xpath("//h2/text()[normalize-space()='Services']")
    assert document.xpath("//p/text()[normalize-space()='Fresh Orchard Juice']")
    assert document.xpath("//p/text()[normalize-space()='Nature Therapy']")

    assert document.xpath("//h2/text()[normalize-space()='Last login']")
    assert not document.xpath("//p/text()[normalize-space()='0 failed login attempts']")


def test_user_information_page_displays_if_there_are_failed_login_attempts(
    client,
    platform_admin_user,
    mocker
):
    mocker.patch('app.user_api_client.get_user', side_effect=[
        platform_admin_user,
        User(user_json(name="Apple Bloom", failed_login_count=2))
    ], autospec=True)
    client.login(platform_admin_user)
    response = client.get(url_for('main.user_information', user_id=345))
    assert response.status_code == 200

    document = html.fromstring(response.get_data(as_text=True))
    assert document.xpath("//p/text()[normalize-space()='2 failed login attempts']")
