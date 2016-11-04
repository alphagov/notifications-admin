from unittest.mock import call, ANY, Mock

import pytest
from flask import url_for
from bs4 import BeautifulSoup
from werkzeug.exceptions import InternalServerError

import app
from app.utils import email_safe
from tests import validate_route_permission, service_json


def test_should_show_overview(
    app_,
    active_user_with_permissions,
    mocker,
    service_one,
    mock_get_organisation
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(active_user_with_permissions, mocker, service_one)
        response = client.get(url_for(
            'main.service_settings', service_id=service_one['id']
        ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('h1').text == 'Settings'
    for index, row in enumerate([
        'Service name service one Change',
        'Email reply to address None Change',
        'Text message sender 40604 Change'
    ]):
        assert row == " ".join(page.find_all('tr')[index + 1].text.split())
    app.service_api_client.get_service.assert_called_with(service_one['id'])


def test_should_show_overview_for_service_with_more_things_set(
    app_,
    active_user_with_permissions,
    mocker,
    service_with_reply_to_addresses,
    mock_get_organisation
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(active_user_with_permissions, mocker, service_with_reply_to_addresses)
        response = client.get(url_for(
            'main.service_settings', service_id=service_with_reply_to_addresses['id']
        ))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    for index, row in enumerate([
        'Service name service one Change',
        'Email reply to address test@example.com Change',
        'Text message sender elevenchars Change'
    ]):
        assert row == " ".join(page.find_all('tr')[index + 1].text.split())


def test_should_show_service_name(app_,
                                  active_user_with_permissions,
                                  mocker,
                                  service_one):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            response = client.get(url_for(
                'main.service_name_change', service_id=service_one['id']))
        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.find('h1').text == 'Change your service name'
        assert page.find('input', attrs={"type": "text"})['value'] == 'service one'
        app.service_api_client.get_service.assert_called_with(service_one['id'])


def test_should_redirect_after_change_service_name(app_,
                                                   service_one,
                                                   active_user_with_permissions,
                                                   mock_login,
                                                   mock_get_user,
                                                   mock_get_service,
                                                   mock_update_service,
                                                   mock_get_services,
                                                   mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions)
            response = client.post(
                url_for('main.service_name_change', service_id=service_one['id']),
                data={'name': "new name"})

        assert response.status_code == 302
        settings_url = url_for(
            'main.service_name_change_confirm', service_id=service_one['id'], _external=True)
        assert settings_url == response.location
        assert mock_get_services.called


def test_show_restricted_service(
    app_,
    service_one,
    mock_login,
    mock_get_user,
    active_user_with_permissions,
    mock_has_permissions,
    mock_get_service,
    mock_get_organisation,
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(active_user_with_permissions)
        response = client.get(url_for('main.service_settings', service_id=service_one['id']))
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.find('h1').text == 'Settings'
        assert page.find_all('h2')[1].text == 'Your service is in trial mode'


def test_switch_service_to_live(
    app_,
    service_one,
    mock_login,
    mock_get_user,
    active_user_with_permissions,
    mock_get_service,
    mock_update_service,
    mock_has_permissions,
    mock_get_organisation
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions)
            response = client.get(
                url_for('main.service_switch_live', service_id=service_one['id']))
        assert response.status_code == 302
        assert response.location == url_for(
            'main.service_settings',
            service_id=service_one['id'], _external=True)
        mock_update_service.assert_called_with(
            service_one['id'],
            message_limit=250000,
            restricted=False
        )


def test_show_live_service(
    app_,
    service_one,
    mock_login,
    mock_get_user,
    active_user_with_permissions,
    mock_get_live_service,
    mock_has_permissions,
    mock_get_organisation,
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(active_user_with_permissions)
        response = client.get(url_for('main.service_settings', service_id=service_one['id']))
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.find('h1').text.strip() == 'Settings'
        assert 'Your service is in trial mode' not in page.text


def test_switch_service_to_restricted(
    app_,
    service_one,
    mock_login,
    mock_get_user,
    active_user_with_permissions,
    mock_get_live_service,
    mock_update_service,
    mock_has_permissions,
    mock_get_organisation
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions)
            response = client.get(
                url_for('main.service_switch_live', service_id=service_one['id']))
        assert response.status_code == 302
        assert response.location == url_for(
            'main.service_settings',
            service_id=service_one['id'], _external=True)
        mock_update_service.assert_called_with(
            service_one['id'],
            message_limit=50,
            restricted=True
        )


def test_should_not_allow_duplicate_names(app_,
                                          active_user_with_permissions,
                                          mocker,
                                          service_one):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            mocker.patch('app.service_api_client.find_all_service_email_from',
                         return_value=['service_one', 'service.two'])
            service_id = service_one['id']
            response = client.post(
                url_for('main.service_name_change', service_id=service_id),
                data={'name': "SErvICE TWO"})

        assert response.status_code == 200
        resp_data = response.get_data(as_text=True)
        assert 'This service name is already in use' in resp_data
        app.service_api_client.find_all_service_email_from.assert_called_once_with()


def test_should_show_service_name_confirmation(app_,
                                               active_user_with_permissions,
                                               mocker,
                                               service_one):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)

            response = client.get(url_for(
                'main.service_name_change_confirm', service_id=service_one['id']))

        assert response.status_code == 200
        resp_data = response.get_data(as_text=True)
        assert 'Change your service name' in resp_data
        app.service_api_client.get_service.assert_called_with(service_one['id'])


def test_should_redirect_after_service_name_confirmation(
    app_,
    active_user_with_permissions,
    service_one,
    mocker,
    mock_update_service,
    mock_verify_password,
    mock_get_organisation
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            service_id = service_one['id']
            service_new_name = 'New Name'
            with client.session_transaction() as session:
                session['service_name_change'] = service_new_name
            response = client.post(url_for(
                'main.service_name_change_confirm', service_id=service_id))

        assert response.status_code == 302
        settings_url = url_for('main.service_settings', service_id=service_id, _external=True)
        assert settings_url == response.location
        mock_update_service.assert_called_once_with(
            service_id,
            name=service_new_name,
            email_from=email_safe(service_new_name)
        )
        assert mock_verify_password.called


def test_should_raise_duplicate_name_handled(app_,
                                             active_user_with_permissions,
                                             service_one,
                                             mocker,
                                             mock_get_services,
                                             mock_update_service_raise_httperror_duplicate_name,
                                             mock_verify_password,
                                             fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            service_new_name = 'New Name'
            with client.session_transaction() as session:
                session['service_name_change'] = service_new_name
            response = client.post(url_for(
                'main.service_name_change_confirm', service_id=service_one['id']))

        assert response.status_code == 302
        name_change_url = url_for(
            'main.service_name_change', service_id=service_one['id'], _external=True)
        assert name_change_url == response.location
        assert mock_update_service_raise_httperror_duplicate_name.called
        assert mock_verify_password.called


def test_should_show_request_to_go_live(app_,
                                        api_user_active,
                                        mock_get_service,
                                        mock_get_user,
                                        mock_get_user_by_email,
                                        mock_login,
                                        mock_has_permissions,
                                        fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = fake_uuid
            response = client.get(
                url_for('main.service_request_to_go_live', service_id=service_id))
        service = mock_get_service.side_effect(service_id)['data']
        assert response.status_code == 200
        resp_data = response.get_data(as_text=True)
        assert 'Request to go live' in resp_data
        assert mock_get_service.called


def test_should_redirect_after_request_to_go_live(
    app_,
    api_user_active,
    mock_get_user,
    mock_get_service,
    mock_has_permissions,
    mock_get_organisation,
    mocker
):
    mock_post = mocker.patch(
        'app.main.views.feedback.requests.post',
        return_value=Mock(status_code=201))
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.post(
                url_for('main.service_request_to_go_live', service_id='6ce466d0-fd6a-11e5-82f5-e0accb9d11a6'),
                data={
                    'mou': 'yes',
                    'channel': 'emails',
                    'start_date': '01/01/2017',
                    'start_volume': '100,000',
                    'peak_volume': '2,000,000',
                    'upload_or_api': 'API'
                },
                follow_redirects=True
            )
            assert response.status_code == 200
            mock_post.assert_called_with(
                ANY,
                data={
                    'subject': 'Request to go live',
                    'department_id': ANY,
                    'agent_team_id': ANY,
                    'message': ANY,
                    'person_name': api_user_active.name,
                    'person_email': api_user_active.email_address
                },
                headers=ANY
            )

            returned_message = mock_post.call_args[1]['data']['message']
            assert 'emails' in returned_message
            assert '01/01/2017' in returned_message
            assert '100,000' in returned_message
            assert '2,000,000' in returned_message
            assert 'API' in returned_message

        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        flash_banner = page.find('div', class_='banner-default').string.strip()
        h1 = page.find('h1').string.strip()
        assert flash_banner == 'We’ve received your request to go live'
        assert h1 == 'Settings'


def test_log_error_on_request_to_go_live(
    app_,
    api_user_active,
    mock_get_user,
    mock_get_service,
    mock_has_permissions,
    mocker
):
    mock_post = mocker.patch(
        'app.main.views.service_settings.requests.post',
        return_value=Mock(
            status_code=401,
            json=lambda: {
                'error_code': 'invalid_auth',
                'error_message': 'Please provide a valid API key or token'
            }
        )
    )
    with app_.test_request_context():
        mock_logger = mocker.patch.object(app_.logger, 'error')
        with app_.test_client() as client:
            client.login(api_user_active)
            with pytest.raises(InternalServerError):
                resp = client.post(
                    url_for('main.service_request_to_go_live', service_id='6ce466d0-fd6a-11e5-82f5-e0accb9d11a6'),
                    data={
                        'mou': 'yes',
                        'channel': 'emails',
                        'start_date': 'start_date',
                        'start_volume': 'start_volume',
                        'peak_volume': 'peak_volume',
                        'upload_or_api': 'API'
                    }
                )
            mock_logger.assert_called_with(
                "Deskpro create ticket request failed with {} '{}'".format(mock_post().status_code, mock_post().json())
            )


def test_should_show_delete_page(app_,
                                 api_user_active,
                                 mock_login,
                                 mock_get_service,
                                 mock_get_user,
                                 mock_get_user_by_email,
                                 mock_has_permissions,
                                 fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = fake_uuid
            response = client.get(url_for(
                'main.service_delete', service_id=service_id))

        assert response.status_code == 200
        assert 'Delete this service from GOV.UK Notify' in response.get_data(as_text=True)
        assert mock_get_service.called


def test_should_show_redirect_after_deleting_service(app_,
                                                     api_user_active,
                                                     mock_get_service,
                                                     mock_get_user,
                                                     mock_get_user_by_email,
                                                     mock_login,
                                                     mock_has_permissions,
                                                     fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = fake_uuid
            response = client.post(url_for(
                'main.service_delete', service_id=service_id))

        assert response.status_code == 302
        delete_url = url_for(
            'main.service_delete_confirm', service_id=service_id, _external=True)
        assert delete_url == response.location


def test_should_show_delete_confirmation(app_,
                                         api_user_active,
                                         mock_get_service,
                                         mock_get_user,
                                         mock_get_user_by_email,
                                         mock_login,
                                         mock_has_permissions,
                                         fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = fake_uuid
            response = client.get(url_for(
                'main.service_delete_confirm', service_id=service_id))

        assert response.status_code == 200
        assert 'Delete this service from Notify' in response.get_data(as_text=True)
        assert mock_get_service.called


def test_should_redirect_delete_confirmation(app_,
                                             api_user_active,
                                             mock_get_service,
                                             mock_delete_service,
                                             mock_get_user,
                                             mock_get_user_by_email,
                                             mock_login,
                                             mock_verify_password,
                                             mock_has_permissions,
                                             fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = fake_uuid
            response = client.post(url_for(
                'main.service_delete_confirm', service_id=service_id))

        assert response.status_code == 302
        choose_url = url_for(
            'main.choose_service', _external=True)
        assert choose_url == response.location
        assert mock_get_service.called
        assert mock_delete_service.called


@pytest.mark.parametrize('route', [
    'main.service_settings',
    'main.service_name_change',
    'main.service_name_change_confirm',
    'main.service_request_to_go_live',
    'main.service_delete',
    'main.service_delete_confirm'
])
def test_route_permissions(mocker, app_, api_user_active, service_one, route):
    with app_.test_request_context():
        validate_route_permission(
            mocker,
            app_,
            "GET",
            200,
            url_for(route, service_id=service_one['id']),
            ['manage_settings'],
            api_user_active,
            service_one)


@pytest.mark.parametrize('route', [
    'main.service_settings',
    'main.service_name_change',
    'main.service_name_change_confirm',
    'main.service_request_to_go_live',
    'main.service_switch_live',
    'main.service_switch_research_mode',
    'main.service_switch_can_send_letters',
    'main.service_delete',
    'main.service_delete_confirm'
])
def test_route_invalid_permissions(mocker, app_, api_user_active, service_one, route):
    with app_.test_request_context():
        validate_route_permission(
            mocker,
            app_,
            "GET",
            403,
            url_for(route, service_id=service_one['id']),
            ['blah'],
            api_user_active,
            service_one)


@pytest.mark.parametrize('route', [
    'main.service_settings',
    'main.service_name_change',
    'main.service_name_change_confirm',
    'main.service_request_to_go_live',
    'main.service_delete',
    'main.service_delete_confirm'
])
def test_route_for_platform_admin(mocker, app_, platform_admin_user, service_one, route):
    with app_.test_request_context():
        validate_route_permission(mocker,
                                  app_,
                                  "GET",
                                  200,
                                  url_for(route, service_id=service_one['id']),
                                  [],
                                  platform_admin_user,
                                  service_one)


def test_route_for_platform_admin_update_service(mocker, app_, platform_admin_user, service_one):
    routes = [
        'main.service_switch_live',
        'main.service_switch_research_mode',
        'main.service_switch_can_send_letters'
    ]
    with app_.test_request_context():
        for route in routes:
            validate_route_permission(mocker,
                                      app_,
                                      "GET",
                                      302,
                                      url_for(route, service_id=service_one['id']),
                                      [],
                                      platform_admin_user,
                                      service_one)


def test_set_reply_to_email_address(
    app_,
    active_user_with_permissions,
    mocker,
    mock_update_service,
    service_one,
    mock_get_organisation
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            data = {"email_address": "test@someservice.gov.uk"}
            response = client.post(url_for('main.service_set_reply_to_email', service_id=service_one['id']),
                                   data=data,
                                   follow_redirects=True)
        assert response.status_code == 200
        mock_update_service.assert_called_with(
            service_one['id'],
            reply_to_email_address="test@someservice.gov.uk"
        )


def test_if_reply_to_email_address_set_then_form_populated(app_,
                                                           active_user_with_permissions,
                                                           mocker,
                                                           service_one):
    service_one['reply_to_email_address'] = 'test@service.gov.uk'
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            response = client.get(url_for('main.service_set_reply_to_email', service_id=service_one['id']))

        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.find(id='email_address')['value'] == 'test@service.gov.uk'


def test_switch_service_to_research_mode(
    app_,
    service_one,
    mock_login,
    mock_get_user,
    active_user_with_permissions,
    mock_get_service,
    mock_has_permissions,
    mocker
):
    with app_.test_request_context(), app_.test_client() as client:
        mocker.patch('app.service_api_client.post', return_value=service_one)

        client.login(active_user_with_permissions)
        response = client.get(url_for('main.service_switch_research_mode', service_id=service_one['id']))
        assert response.status_code == 302
        assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
        app.service_api_client.post.assert_called_with(
            '/service/{}'.format(service_one['id']),
            {
                'research_mode': True,
                'created_by': active_user_with_permissions.id
            }
        )


def test_switch_service_from_research_mode_to_normal(
        app_,
        service_one,
        mock_login,
        mock_get_user,
        active_user_with_permissions,
        mock_get_service,
        mock_has_permissions,
        mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            service = service_json(
                "1234",
                "Test Service",
                [active_user_with_permissions.id],
                message_limit=1000,
                active=False,
                restricted=True,
                research_mode=True
            )
            mocker.patch('app.service_api_client.get_service', return_value={"data": service})
            mocker.patch('app.service_api_client.update_service_with_properties', return_value=service_one)

            client.login(active_user_with_permissions)
            response = client.get(url_for('main.service_switch_research_mode', service_id=service_one['id']))
            assert response.status_code == 302
            assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
            app.service_api_client.update_service_with_properties.assert_called_with(
                service_one['id'], {"research_mode": False}
            )


def test_shows_research_mode_indicator(
    app_,
    service_one,
    mock_login,
    mock_get_user,
    active_user_with_permissions,
    mock_get_service,
    mock_has_permissions,
    mock_get_organisation,
    mocker
):
    with app_.test_request_context():
        with app_.test_client() as client:
            service = service_json(
                "1234",
                "Test Service",
                [active_user_with_permissions.id],
                message_limit=1000,
                active=False,
                restricted=True,
                research_mode=True
            )
            mocker.patch('app.service_api_client.get_service', return_value={"data": service})
            mocker.patch('app.service_api_client.update_service_with_properties', return_value=service_one)

            client.login(active_user_with_permissions)
            response = client.get(url_for('main.service_settings', service_id=service_one['id']))
            assert response.status_code == 200

            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            element = page.find('span', {"id": "research-mode"})
            assert element.text == 'research mode'


def test_does_not_show_research_mode_indicator(
    app_,
    service_one,
    mock_login,
    mock_get_user,
    active_user_with_permissions,
    mock_get_service,
    mock_has_permissions,
    mock_get_organisation,
    mocker
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions)
            response = client.get(url_for('main.service_settings', service_id=service_one['id']))
            assert response.status_code == 200

            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            element = page.find('span', {"id": "research-mode"})
            assert not element


def test_set_text_message_sender(
    app_,
    active_user_with_permissions,
    mocker,
    mock_update_service,
    service_one,
    mock_get_organisation
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            data = {"sms_sender": "elevenchars"}
            response = client.post(url_for('main.service_set_sms_sender', service_id=service_one['id']),
                                   data=data,
                                   follow_redirects=True)
        assert response.status_code == 200

        mock_update_service.assert_called_with(
            service_one['id'],
            sms_sender="elevenchars"
        )


def test_if_sms_sender_set_then_form_populated(app_,
                                               active_user_with_permissions,
                                               mocker,
                                               service_one):
    service_one['sms_sender'] = 'elevenchars'
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            response = client.get(url_for('main.service_set_sms_sender', service_id=service_one['id']))

        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.find(id='sms_sender')['value'] == 'elevenchars'


def test_should_show_branding(
    mocker, app_, platform_admin_user, service_one, mock_get_organisations
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(platform_admin_user, mocker, service_one)
        response = client.get(url_for(
            'main.service_set_branding_and_org', service_id=service_one['id']
        ))
        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

        assert page.find('input', attrs={"id": "branding_type-0"})['value'] == 'govuk'
        assert page.find('input', attrs={"id": "branding_type-1"})['value'] == 'both'
        assert page.find('input', attrs={"id": "branding_type-2"})['value'] == 'org'

        assert 'checked' in page.find('input', attrs={"id": "branding_type-0"}).attrs
        assert 'checked' not in page.find('input', attrs={"id": "branding_type-1"}).attrs
        assert 'checked' not in page.find('input', attrs={"id": "branding_type-2"}).attrs

        app.organisations_client.get_organisations.assert_called_once_with()
        app.service_api_client.get_service.assert_called_once_with(service_one['id'])


def test_should_show_organisations(
    mocker, app_, platform_admin_user, service_one, mock_get_organisations
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(platform_admin_user, mocker, service_one)
        response = client.get(url_for(
            'main.service_set_branding_and_org', service_id=service_one['id']
        ))
        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

        assert page.find('input', attrs={"id": "branding_type-0"})['value'] == 'govuk'
        assert page.find('input', attrs={"id": "branding_type-1"})['value'] == 'both'
        assert page.find('input', attrs={"id": "branding_type-2"})['value'] == 'org'

        assert 'checked' in page.find('input', attrs={"id": "branding_type-0"}).attrs
        assert 'checked' not in page.find('input', attrs={"id": "branding_type-1"}).attrs
        assert 'checked' not in page.find('input', attrs={"id": "branding_type-2"}).attrs

        app.organisations_client.get_organisations.assert_called_once_with()
        app.service_api_client.get_service.assert_called_once_with(service_one['id'])


def test_should_set_branding_and_organisations(
    mocker, app_, platform_admin_user, service_one, mock_get_organisations, mock_update_service
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(platform_admin_user, mocker, service_one)
        response = client.post(
            url_for(
                'main.service_set_branding_and_org', service_id=service_one['id']
            ),
            data={
                'branding_type': 'org',
                'organisation': 'organisation-id'
            }
        )
        assert response.status_code == 302
        assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)

        app.organisations_client.get_organisations.assert_called_once_with()
        app.service_api_client.update_service.assert_called_once_with(
            service_one['id'],
            branding='org',
            organisation='organisation-id'
        )


def test_switch_service_enable_letters(client, platform_admin_user, service_one, mocker):
    mocked_fn = mocker.patch('app.service_api_client.update_service_with_properties', return_value=service_one)

    client.login(platform_admin_user, mocker, service_one)
    response = client.get(url_for('main.service_switch_can_send_letters', service_id=service_one['id']))

    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    assert mocked_fn.call_args == call(service_one['id'], {'can_send_letters': True})


def test_switch_service_disable_letters(client, platform_admin_user, mocker):
    service = service_json("1234", "Test Service", [], can_send_letters=True)
    mocker.patch('app.service_api_client.get_service', return_value={"data": service})
    mocked_fn = mocker.patch('app.service_api_client.update_service_with_properties', return_value=service)

    client.login(platform_admin_user, mocker, service)
    response = client.get(url_for('main.service_switch_can_send_letters', service_id=service['id']))

    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service['id'], _external=True)
    assert mocked_fn.call_args == call(service['id'], {"can_send_letters": False})
