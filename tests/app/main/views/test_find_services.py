from flask import url_for

from tests import service_json


def test_find_services_by_name_page_loads_correctly(client_request, platform_admin_user):
    client_request.login(platform_admin_user)
    document = client_request.get('main.find_services_by_name')

    assert document.h1.text.strip() == 'Find services by name'
    assert len(document.find_all('input', {'type': 'search'})) > 0


def test_find_services_by_name_displays_services_found(
    client_request,
    platform_admin_user,
    mocker
):
    client_request.login(platform_admin_user)
    get_services = mocker.patch(
        'app.service_api_client.find_services_by_name',
        return_value={"data": [service_json()]}
    )
    document = client_request.post(
        'main.find_services_by_name',
        _data={"search": "Test Service"},
        _expected_status=200
    )
    get_services.assert_called_once_with(service_name="Test Service")
    result = document.select_one('.browse-list-item a')
    assert result.text.strip() == 'Test Service'
    assert result.attrs["href"] == "/services/1234"


def test_find_services_by_name_displays_multiple_services(
    client_request,
    platform_admin_user,
    mocker
):
    client_request.login(platform_admin_user)
    mocker.patch(
        'app.service_api_client.find_services_by_name',
        return_value={"data": [service_json(name="Tadfield Police"), service_json(name="Tadfield Air Base")]}
    )
    document = client_request.post('main.find_services_by_name', _data={"search": "Tadfield"}, _expected_status=200)

    results = document.find_all('li', {'class': 'browse-list-item'})
    assert len(results) == 2
    assert sorted([result.text.strip() for result in results]) == ["Tadfield Air Base", "Tadfield Police"]


def test_find_services_by_name_displays_message_if_no_services_found(
    client_request,
    platform_admin_user,
    mocker
):
    client_request.login(platform_admin_user)
    mocker.patch('app.service_api_client.find_services_by_name', return_value={"data": []})
    document = client_request.post(
        'main.find_services_by_name', _data={"search": "Nabuchodonosorian Empire"}, _expected_status=200
    )

    assert document.find('p', {'class': 'browse-list-hint'}).text.strip() == 'No services found.'


def test_find_services_by_name_validates_against_empty_search_submission(
    client_request,
    platform_admin_user,
    mocker
):
    client_request.login(platform_admin_user)
    document = client_request.post('main.find_services_by_name', _data={"search": ""}, _expected_status=200)

    expected_message = "Error: You need to enter full or partial name to search by."
    assert document.find('span', {'class': 'govuk-error-message'}).text.strip() == expected_message


def test_find_services_by_name_redirects_for_uuid(
    client_request,
    platform_admin_user,
    mocker,
    fake_uuid
):
    client_request.login(platform_admin_user)
    client_request.post(
        'main.find_services_by_name',
        _data={"search": fake_uuid},
        _expected_redirect=url_for(
            'main.service_dashboard',
            service_id=fake_uuid,
        ),
    )
