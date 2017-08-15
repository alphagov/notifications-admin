import app
import pytest
from bs4 import BeautifulSoup
from flask import url_for
from notifications_python_client.errors import HTTPError


def test_set_text_message_sender(
        logged_in_client,
        mock_update_service,
        service_one
):
    data = {"sms_sender": "elevenchars"}
    response = logged_in_client.post(url_for('main.service_set_sms_sender', service_id=service_one['id']),
                                     data=data)
    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)

    mock_update_service.assert_called_with(
        service_one['id'],
        sms_sender="elevenchars"
    )


def test_get_inbound_number_in_service_settings(
        logged_in_client,
        mock_update_service,
        mock_get_letter_organisations,
        service_one,
        mocker
):
    mocker_get_inbound_number_fun = mocker.patch(
        'app.inbound_number_client.get_inbound_sms_number_for_service',
        return_value={'data': {'number': '077777777', 'id': 'some_uuid'}})

    response = logged_in_client.get(url_for('main.service_settings', service_id=service_one['id']))
    assert response.status_code == 200
    mocker_get_inbound_number_fun.assert_called_once_with(service_one['id'])

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    element = page.find('span', {"id": "077777777"})
    assert not element


def test_allow_inbound_sms_sets_a_number_for_service(
        logged_in_client,
        service_one,
        mocker
):
    mocker.patch('app.service_api_client.update_service_with_properties')
    mock_activate_inbound_sms = mocker.patch('app.inbound_number_client.activate_inbound_sms_service')

    response = logged_in_client.get(url_for('main.service_set_inbound_number',
                                            service_id=service_one['id'],
                                            set_inbound_sms=True))

    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    mock_activate_inbound_sms.assert_called_once_with(service_one['id'])


def test_allow_inbound_sms_returns_400_if_no_numbers_available(
        logged_in_client,
        service_one,
        mocker
):
    mock_switch_service = mocker.patch('app.service_api_client.update_service_with_properties')
    mock_activate_inbound = mocker.patch('app.inbound_number_client.activate_inbound_sms_service',
                                         side_effect=HTTPError)
    logged_in_client.get(
        url_for('main.service_set_inbound_number', service_id=service_one['id'], set_inbound_sms='True'))
    mock_activate_inbound.assert_called_once_with(service_one['id'])
    assert mock_switch_service.call_count == 2


def test_set_text_message_sender_and_inbound_sms_permission_exists_return_403(
        logged_in_client,
        service_one,
        mocker,
):
    service_one['permissions'] = ['inbound_sms']
    mocker.patch('app.service_api_client.get_service', return_value={'data': service_one})
    update_service_mock = mocker.patch('app.service_api_client.update_service_with_properties')

    data = {"sms_sender": "elevenchars"}
    response = logged_in_client.post(url_for('main.service_set_sms_sender', service_id=service_one['id']),
                                     data=data)

    assert response.status_code == 403

    assert not update_service_mock.called
    assert app.current_service['permissions'] == ['inbound_sms']


def test_turn_inbound_sms_off(
        logged_in_client,
        service_one,
        mocker
):
    service_one['permissions'] = ['inbound_sms']
    update_service_mock = mocker.patch('app.service_api_client.update_service',
                                       return_value=service_one)
    mock_deactivate_inbound = mocker.patch('app.inbound_number_client.deactivate_inbound_sms_permission')

    response = logged_in_client.get(url_for('main.service_set_inbound_number', service_id=service_one['id'],
                                            set_inbound_sms=False))
    assert response.status_code == 302
    assert response.location == url_for('main.service_set_sms_sender', service_id=service_one['id'], _external=True)

    assert app.current_service['permissions'] == []
    mock_deactivate_inbound.assert_called_once_with(service_id=service_one['id'])
    assert update_service_mock.called


def test_set_text_message_sender_and_not_inbound_sms(
        logged_in_client,
        service_one,
        mocker
):
    service_one['permissions'] = []
    update_service_mock = mocker.patch('app.service_api_client.update_service',
                                       return_value=service_one)

    data = {"sms_sender": "elevenchars"}
    response = logged_in_client.post(url_for('main.service_set_sms_sender', service_id=service_one['id'],
                                             set_inbound_sms=False),
                                     data=data)
    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)

    update_service_mock.assert_called_with(
        service_one['id'],
        sms_sender="elevenchars"
    )
    assert app.current_service['permissions'] == []


@pytest.mark.parametrize('content, expected_error', [
    ("", "Can’t be empty"),
    ("twelvecharss", "Enter 11 characters or fewer"),
    (".", "Use letters and numbers only")
])
def test_set_text_message_sender_validation(
        logged_in_client,
        mock_update_service,
        service_one,
        content,
        expected_error,
):
    response = logged_in_client.post(url_for(
        'main.service_set_sms_sender',
        service_id=service_one['id']),
        data={"sms_sender": content},
        follow_redirects=True
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert response.status_code == 200
    assert page.select(".error-message")[0].text.strip() == expected_error
    assert not mock_update_service.called


def test_if_sms_sender_set_then_form_populated(
        logged_in_client,
        service_one,
        mock_get_inbound_number_for_service
):
    service_one['sms_sender'] = 'elevenchars'
    response = logged_in_client.get(url_for('main.service_set_sms_sender', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find(id='sms_sender')['value'] == 'elevenchars'