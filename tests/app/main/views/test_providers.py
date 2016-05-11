from bs4 import BeautifulSoup
from flask import url_for
import copy
import re
import app

stub_providers = {
    'provider_details': [
        {
            'id': '6005e192-4738-4962-beec-ebd982d0b03f',
            'active': True,
            'priority': 1,
            'display_name': 'first_sms_provider',
            'identifier': 'first_sms',
            'notification_type': 'sms'
        },
        {
            'active': True,
            'priority': 2,
            'display_name': 'second_sms_provider',
            'identifier': 'second_sms',
            'id': '0bd529cd-a0fd-43e5-80ee-b95ef6b0d51f',
            'notification_type': 'sms'
        },
        {
            'id': '6005e192-4738-4962-beec-ebd982d0b03a',
            'active': True,
            'priority': 1,
            'display_name': 'first_email_provider',
            'identifier': 'first_email',
            'notification_type': 'email'
        },
        {
            'active': True,
            'priority': 2,
            'display_name': 'second_email_provider',
            'identifier': 'second_email',
            'id': '0bd529cd-a0fd-43e5-80ee-b95ef6b0d51b',
            'notification_type': 'email'
        }
    ]
}

stub_provider = {
    'provider_details':
        {
            'id': '6005e192-4738-4962-beec-ebd982d0b03f',
            'active': True,
            'priority': 1,
            'display_name': 'first_sms_provider',
            'identifier': 'first_sms',
            'notification_type': 'sms'
        }
}


def test_should_show_all_providers(
        app_,
        platform_admin_user,
        mock_login,
        mock_has_permissions,
        mocker
):
    mock_providers = mocker.patch(
        'app.provider_client.get_all_providers',
        return_value=copy.deepcopy(stub_providers)
    )

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(platform_admin_user)
            response = client.get(url_for('main.view_providers'))

            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

            h1 = [header.text.strip() for header in page.find_all('h1')]

            assert 'Providers' in h1

            h2 = [header.text.strip() for header in page.find_all('h2')]

            assert 'Email' in h2
            assert 'SMS' in h2

            tables = page.find_all('table')
            assert len(tables) == 2

            sms_table = tables[0]
            email_table = tables[1]

            sms_first_row = sms_table.tbody.find_all('tr')[0]
            table_data = sms_first_row.find_all('td')

            assert table_data[0].text.strip() == "first_sms_provider"
            assert table_data[1].text.strip() == "1"
            assert table_data[2].text.strip() == "True"
            assert table_data[3].find_all("a")[0]['href'] == '/provider/6005e192-4738-4962-beec-ebd982d0b03f'

            sms_second_row = sms_table.tbody.find_all('tr')[1]
            table_data = sms_second_row.find_all('td')

            assert table_data[0].text.strip() == "second_sms_provider"
            assert table_data[1].text.strip() == "2"
            assert table_data[2].text.strip() == "True"
            assert table_data[3].find_all("a")[0]['href'] == '/provider/0bd529cd-a0fd-43e5-80ee-b95ef6b0d51f'

            email_first_row = email_table.tbody.find_all('tr')[0]
            email_table_data = email_first_row.find_all('td')

            assert email_table_data[0].text.strip() == "first_email_provider"
            assert email_table_data[1].text.strip() == "1"
            assert email_table_data[2].text.strip() == "True"
            assert email_table_data[3].find_all("a")[0]['href'] == '/provider/6005e192-4738-4962-beec-ebd982d0b03a'

            email_second_row = email_table.tbody.find_all('tr')[1]
            email_table_data = email_second_row.find_all('td')

            assert email_table_data[0].text.strip() == "second_email_provider"
            assert email_table_data[1].text.strip() == "2"
            assert email_table_data[2].text.strip() == "True"
            assert email_table_data[3].find_all("a")[0]['href'] == '/provider/0bd529cd-a0fd-43e5-80ee-b95ef6b0d51b'


def test_should_show_provider_detail(
        app_,
        platform_admin_user,
        mock_login,
        mock_has_permissions,
        mocker
):
    mock_providers = mocker.patch(
        'app.provider_client.get_provider_by_id',
        return_value=copy.deepcopy(stub_provider)
    )

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(platform_admin_user)
            response = client.get(url_for('main.view_provider', provider_id='12345'))

            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

            h1 = [header.text.strip() for header in page.find_all('h1')]

            assert 'first_sms_provider' in h1

            form = [form for form in page.find_all('form')]

            form_elements = [element for element in form[0].find_all('input')]
            assert form_elements[0]['value'] == '1'
            assert form_elements[0]['name'] == 'priority'


def test_should_show_error_on_bad_provider_priority(
        app_,
        platform_admin_user,
        mock_login,
        mock_has_permissions,
        mocker
):
    mock_providers = mocker.patch(
        'app.provider_client.get_provider_by_id',
        return_value=copy.deepcopy(stub_provider)
    )

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(platform_admin_user)
            response = client.post(
                url_for('main.view_provider', provider_id=stub_provider['provider_details']['id']),
                data={'priority': "not valid"})

        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert response.status_code == 200
        assert "Not a valid integer value" in str(page.find_all("span", {"class": re.compile(r"error-message")})[0])


def test_should_show_error_on_negative_provider_priority(
        app_,
        platform_admin_user,
        mock_login,
        mock_has_permissions,
        mocker
):
    mock_providers = mocker.patch(
        'app.provider_client.get_provider_by_id',
        return_value=copy.deepcopy(stub_provider)
    )

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(platform_admin_user)
            response = client.post(
                url_for('main.view_provider', provider_id=stub_provider['provider_details']['id']),
                data={'priority': -1})

        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert response.status_code == 200
        assert "Must be between 1 and 100" in str(page.find_all("span", {"class": re.compile(r"error-message")})[0])


def test_should_show_error_on_too_big_provider_priority(
        app_,
        platform_admin_user,
        mock_login,
        mock_has_permissions,
        mocker
):
    mock_providers = mocker.patch(
        'app.provider_client.get_provider_by_id',
        return_value=copy.deepcopy(stub_provider)
    )

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(platform_admin_user)
            response = client.post(
                url_for('main.view_provider', provider_id=stub_provider['provider_details']['id']),
                data={'priority': 101})

        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert response.status_code == 200
        assert "Must be between 1 and 100" in str(page.find_all("span", {"class": re.compile(r"error-message")})[0])


def test_should_show_error_on_too_little_provider_priority(
        app_,
        platform_admin_user,
        mock_login,
        mock_has_permissions,
        mocker
):
    mock_providers = mocker.patch(
        'app.provider_client.get_provider_by_id',
        return_value=copy.deepcopy(stub_provider)
    )

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(platform_admin_user)
            response = client.post(
                url_for('main.view_provider', provider_id=stub_provider['provider_details']['id']),
                data={'priority': 0})

        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert response.status_code == 200
        assert "Must be between 1 and 100" in str(page.find_all("span", {"class": re.compile(r"error-message")})[0])


def test_should_update_provider_priority(
        app_,
        platform_admin_user,
        mock_login,
        mock_has_permissions,
        mocker
):

    mock_providers = mocker.patch(
        'app.provider_client.get_provider_by_id',
        return_value=copy.deepcopy(stub_provider)
    )

    mock_updated_providers = mocker.patch(
        'app.provider_client.update_provider',
        return_value=copy.deepcopy(stub_provider)
    )

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(platform_admin_user)
            response = client.post(
                url_for('main.view_provider', provider_id=stub_provider['provider_details']['id']),
                data={'priority': 2})

        app.provider_client.update_provider.assert_called_with(stub_provider['provider_details']['id'], 2)
        assert response.status_code == 302
        assert response.location == 'http://localhost/providers'
