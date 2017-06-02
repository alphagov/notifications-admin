from unittest.mock import call, ANY, Mock

import pytest
import uuid
from flask import url_for
from bs4 import BeautifulSoup
from werkzeug.exceptions import InternalServerError

import app
from app.utils import email_safe
from tests import validate_route_permission, service_json
from tests.app.test_utils import normalize_spaces

from tests.conftest import active_user_with_permissions, platform_admin_user


@pytest.mark.parametrize('user, expected_rows', [
    (active_user_with_permissions, [
        'Label Value Action',
        'Service name service one Change',
        'Email reply to address None Change',
        'Text message sender GOVUK Change',
        'International text messages Off Change',
        'Letters Off Change',
    ]),
    (platform_admin_user, [
        'Label Value Action',
        'Service name service one Change',
        'Email reply to address None Change',
        'Text message sender GOVUK Change',
        'International text messages Off Change',
        'Letters Off Change',
        'Label Value Action',
        'Email branding GOV.UK Change',
        'Letter branding HM Government Change',
    ]),
])
def test_should_show_overview(
    client,
    mocker,
    service_one,
    fake_uuid,
    mock_get_letter_organisations,
    user,
    expected_rows,
):
    client.login(user(fake_uuid), mocker, service_one)
    response = client.get(url_for(
        'main.service_settings', service_id=service_one['id']
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('h1').text == 'Settings'
    rows = page.find_all('tr')
    assert len(rows) == len(expected_rows)
    for index, row in enumerate(expected_rows):
        assert row == " ".join(rows[index].text.split())
    app.service_api_client.get_service.assert_called_with(service_one['id'])


def test_should_show_overview_for_service_with_more_things_set(
    client,
    active_user_with_permissions,
    mocker,
    service_with_reply_to_addresses,
    mock_get_organisation,
    mock_get_letter_organisations,
):
    client.login(active_user_with_permissions, mocker, service_with_reply_to_addresses)
    response = client.get(url_for(
        'main.service_settings', service_id=service_with_reply_to_addresses['id']
    ))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    for index, row in enumerate([
        'Service name service one Change',
        'Email reply to address test@example.com Change',
        'Text message sender elevenchars Change',
        'International text messages Off Change',
        'Letters Off Change',
    ]):
        assert row == " ".join(page.find_all('tr')[index + 1].text.split())


def test_if_cant_send_letters_then_cant_see_letter_contact_block(
    logged_in_client,
    service_one,
    mock_get_letter_organisations,
):
    response = logged_in_client.get(url_for(
        'main.service_settings', service_id=service_one['id']
    ))
    assert 'Letter contact block' not in response.get_data(as_text=True)


def test_if_can_receive_inbound_then_cant_change_sms_sender(
    logged_in_client,
    service_one,
    mock_get_letter_organisations,
):
    service_one['permissions'] = ['inbound_sms']
    service_one['sms_sender'] = 'SomeNumber'
    response = logged_in_client.get(url_for(
        'main.service_settings', service_id=service_one['id']
    ))
    assert 'Text message sender SomeNumber Change' not in response.get_data(as_text=True)
    assert url_for('.service_set_sms_sender', service_id=service_one['id'],
                   set_inbound_sms=False) not in response.get_data(as_text=True)
    assert 'SomeNumber' in response.get_data(as_text=True)


def test_letter_contact_block_shows_none_if_not_set(
    logged_in_client,
    service_one,
    mocker,
    mock_get_letter_organisations,
):
    service_one['can_send_letters'] = True
    response = logged_in_client.get(url_for(
        'main.service_settings', service_id=service_one['id']
    ))

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    div = page.find_all('tr')[6].find_all('td')[1].div
    assert div.text.strip() == 'None'
    assert 'default' in div.attrs['class'][0]


def test_escapes_letter_contact_block(
    logged_in_client,
    service_one,
    mocker,
    mock_get_letter_organisations,
):
    service_one['can_send_letters'] = True
    service_one['letter_contact_block'] = 'foo\nbar<script>alert(1);</script>'
    response = logged_in_client.get(url_for(
        'main.service_settings', service_id=service_one['id']
    ))

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    div = str(page.find_all('tr')[6].find_all('td')[1].div)
    assert 'foo<br>bar' in div
    assert '<script>' not in div


def test_should_show_service_name(
    logged_in_client,
    service_one,
):
    response = logged_in_client.get(url_for(
        'main.service_name_change', service_id=service_one['id']))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('h1').text == 'Change your service name'
    assert page.find('input', attrs={"type": "text"})['value'] == 'service one'
    app.service_api_client.get_service.assert_called_with(service_one['id'])


def test_should_redirect_after_change_service_name(
    logged_in_client,
    service_one,
    mock_update_service,
    mock_get_services,
):
    response = logged_in_client.post(
        url_for('main.service_name_change', service_id=service_one['id']),
        data={'name': "new name"})

    assert response.status_code == 302
    settings_url = url_for(
        'main.service_name_change_confirm', service_id=service_one['id'], _external=True)
    assert settings_url == response.location
    assert mock_get_services.called


def test_show_restricted_service(
    logged_in_client,
    service_one,
    mock_get_letter_organisations,
):
    response = logged_in_client.get(url_for('main.service_settings', service_id=service_one['id']))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('h1').text == 'Settings'
    assert page.find_all('h2')[0].text == 'Your service is in trial mode'


def test_switch_service_to_live(
    logged_in_platform_admin_client,
    service_one,
    mock_update_service,
):
    response = logged_in_platform_admin_client.get(
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
    logged_in_client,
    service_one,
    mock_get_live_service,
    mock_get_letter_organisations,
):
    response = logged_in_client.get(url_for('main.service_settings', service_id=service_one['id']))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('h1').text.strip() == 'Settings'
    assert 'Your service is in trial mode' not in page.text


def test_switch_service_to_restricted(
    logged_in_platform_admin_client,
    service_one,
    mock_get_live_service,
    mock_update_service
):
    response = logged_in_platform_admin_client.get(
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


def test_should_not_allow_duplicate_names(
    logged_in_client,
    mocker,
    service_one,
):
    mocker.patch('app.service_api_client.find_all_service_email_from',
                 return_value=['service_one', 'service.two'])
    service_id = service_one['id']
    response = logged_in_client.post(
        url_for('main.service_name_change', service_id=service_id),
        data={'name': "SErvICE TWO"})

    assert response.status_code == 200
    resp_data = response.get_data(as_text=True)
    assert 'This service name is already in use' in resp_data
    app.service_api_client.find_all_service_email_from.assert_called_once_with()


def test_should_show_service_name_confirmation(
    logged_in_client,
    service_one,
):
    response = logged_in_client.get(url_for(
        'main.service_name_change_confirm', service_id=service_one['id']))

    assert response.status_code == 200
    resp_data = response.get_data(as_text=True)
    assert 'Change your service name' in resp_data
    app.service_api_client.get_service.assert_called_with(service_one['id'])


def test_should_redirect_after_service_name_confirmation(
    logged_in_client,
    service_one,
    mock_update_service,
    mock_verify_password
):
    service_id = service_one['id']
    service_new_name = 'New Name'
    with logged_in_client.session_transaction() as session:
        session['service_name_change'] = service_new_name
    response = logged_in_client.post(url_for(
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


def test_should_raise_duplicate_name_handled(
    logged_in_client,
    service_one,
    mock_update_service_raise_httperror_duplicate_name,
    mock_verify_password
):
    service_new_name = 'New Name'
    with logged_in_client.session_transaction() as session:
        session['service_name_change'] = service_new_name
    response = logged_in_client.post(url_for(
        'main.service_name_change_confirm', service_id=service_one['id']))

    assert response.status_code == 302
    name_change_url = url_for(
        'main.service_name_change', service_id=service_one['id'], _external=True)
    assert name_change_url == response.location
    assert mock_update_service_raise_httperror_duplicate_name.called
    assert mock_verify_password.called


def test_should_show_request_to_go_live(
    logged_in_client,
    mock_get_service,
    service_one
):
    response = logged_in_client.get(
        url_for('main.service_request_to_go_live', service_id=service_one['id']))
    assert response.status_code == 200
    resp_data = response.get_data(as_text=True)
    assert 'Request to go live' in resp_data
    assert mock_get_service.called


def test_should_redirect_after_request_to_go_live(
    logged_in_client,
    active_user_with_permissions,
    service_one,
    mocker,
    mock_get_letter_organisations,
):
    mock_post = mocker.patch(
        'app.main.views.feedback.requests.post',
        return_value=Mock(status_code=201))
    response = logged_in_client.post(
        url_for('main.service_request_to_go_live', service_id=service_one['id']),
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
            'subject': 'Request to go live - service one',
            'department_id': ANY,
            'agent_team_id': ANY,
            'message': ANY,
            'person_name': active_user_with_permissions.name,
            'person_email': active_user_with_permissions.email_address
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
    logged_in_client,
    service_one,
    mocker,
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
    mock_logger = mocker.patch.object(app_.logger, 'error')
    with pytest.raises(InternalServerError):
        logged_in_client.post(
            url_for('main.service_request_to_go_live', service_id=service_one['id']),
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


@pytest.mark.parametrize('route', [
    'main.service_settings',
    'main.service_name_change',
    'main.service_name_change_confirm',
    'main.service_request_to_go_live',
    'main.archive_service'
])
def test_route_permissions(
    mocker,
    app_,
    client,
    api_user_active,
    service_one,
    mock_get_letter_organisations,
    route,
):
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
    'main.service_switch_can_send_international_sms',
    'main.archive_service',
])
def test_route_invalid_permissions(
    mocker,
    app_,
    client,
    api_user_active,
    service_one,
    route,
):
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
])
def test_route_for_platform_admin(
    mocker,
    app_,
    client,
    platform_admin_user,
    service_one,
    mock_get_letter_organisations,
    route,
):
    validate_route_permission(mocker,
                              app_,
                              "GET",
                              200,
                              url_for(route, service_id=service_one['id']),
                              [],
                              platform_admin_user,
                              service_one)


@pytest.mark.parametrize('route', [
    'main.service_switch_live',
    'main.service_switch_research_mode',
    'main.service_switch_can_send_letters',
    'main.service_switch_can_send_international_sms',
])
def test_route_for_platform_admin_update_service(
    mocker,
    app_,
    client,
    platform_admin_user,
    service_one,
    mock_get_letter_organisations,
    route,
):
    mocker.patch('app.service_api_client.archive_service')
    validate_route_permission(mocker,
                              app_,
                              "GET",
                              302,
                              url_for(route, service_id=service_one['id']),
                              [],
                              platform_admin_user,
                              service_one)


def test_set_reply_to_email_address(
    logged_in_client,
    mock_update_service,
    service_one,
    mock_get_letter_organisations,
):
    data = {"email_address": "test@someservice.gov.uk"}
    response = logged_in_client.post(url_for('main.service_set_reply_to_email', service_id=service_one['id']),
                                     data=data,
                                     follow_redirects=True)
    assert response.status_code == 200
    mock_update_service.assert_called_with(
        service_one['id'],
        reply_to_email_address="test@someservice.gov.uk"
    )


def test_if_reply_to_email_address_set_then_form_populated(
    logged_in_client,
    service_one,
):
    service_one['reply_to_email_address'] = 'test@service.gov.uk'
    response = logged_in_client.get(url_for('main.service_set_reply_to_email', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find(id='email_address')['value'] == 'test@service.gov.uk'


def test_switch_service_to_research_mode(
    logged_in_platform_admin_client,
    platform_admin_user,
    service_one,
    mocker,
):
    mocker.patch('app.service_api_client.post', return_value=service_one)
    response = logged_in_platform_admin_client.get(
        url_for('main.service_switch_research_mode', service_id=service_one['id'])
    )
    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    app.service_api_client.post.assert_called_with(
        '/service/{}'.format(service_one['id']),
        {
            'research_mode': True,
            'created_by': platform_admin_user.id
        }
    )


def test_switch_service_from_research_mode_to_normal(
    logged_in_platform_admin_client,
    mocker,
):
    service = service_json(
        research_mode=True
    )
    mocker.patch('app.service_api_client.get_service', return_value={"data": service})
    update_service_mock = mocker.patch('app.service_api_client.update_service_with_properties', return_value=service)

    response = logged_in_platform_admin_client.get(
        url_for('main.service_switch_research_mode', service_id=service['id'])
    )
    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service['id'], _external=True)
    update_service_mock.assert_called_with(
        service['id'], {"research_mode": False}
    )


def test_shows_research_mode_indicator(
    logged_in_client,
    service_one,
    mocker,
    mock_get_letter_organisations,
):
    service_one['research_mode'] = True
    mocker.patch('app.service_api_client.update_service_with_properties', return_value=service_one)

    response = logged_in_client.get(url_for('main.service_settings', service_id=service_one['id']))
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    element = page.find('span', {"id": "research-mode"})
    assert element.text == 'research mode'


def test_does_not_show_research_mode_indicator(
    logged_in_client,
    service_one,
    mock_get_letter_organisations,
):
    response = logged_in_client.get(url_for('main.service_settings', service_id=service_one['id']))
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    element = page.find('span', {"id": "research-mode"})
    assert not element


def test_set_text_message_sender(
    logged_in_client,
    mock_update_service,
    service_one,
    mock_get_letter_organisations,
):
    data = {"sms_sender": "elevenchars"}
    response = logged_in_client.post(url_for('main.service_set_sms_sender', service_id=service_one['id']),
                                     data=data,
                                     follow_redirects=True)
    assert response.status_code == 200

    mock_update_service.assert_called_with(
        service_one['id'],
        sms_sender="elevenchars"
    )


def test_set_text_message_sender_and_inbound_sms(
    logged_in_client,
    service_one,
    mock_get_letter_organisations,
    mocker,
):

    update_service_mock = mocker.patch('app.service_api_client.update_service_with_properties',
                                       return_value=service_one)

    data = {"sms_sender": "elevenchars"}
    response = logged_in_client.post(url_for('main.service_set_sms_sender', service_id=service_one['id'],
                                             set_inbound_sms=True),
                                     data=data,
                                     follow_redirects=True)
    assert response.status_code == 200

    update_service_mock.assert_called_with(
        service_one['id'],
        {'permissions': ['inbound_sms'],
         'sms_sender': "elevenchars"}
    )


@pytest.mark.parametrize('content, expected_error', [
    ("", "Can’t be empty"),
    ("twelvecharss", "Enter 11 characters or fewer"),
    (".", "Use letters and numbers only")
])
def test_set_text_message_sender_validation(
    logged_in_client,
    mock_update_service,
    service_one,
    mock_get_letter_organisations,
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
):
    service_one['sms_sender'] = 'elevenchars'
    response = logged_in_client.get(url_for('main.service_set_sms_sender', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find(id='sms_sender')['value'] == 'elevenchars'


@pytest.mark.parametrize('method', ['get', 'post'])
def test_cant_set_letter_contact_block_if_service_cant_send_letters(
    logged_in_client,
    service_one,
    method
):
    assert not service_one['can_send_letters']
    response = getattr(logged_in_client, method)(
        url_for('main.service_set_letter_contact_block', service_id=service_one['id'])
    )
    assert response.status_code == 403


def test_set_letter_contact_block_prepopulates(
    logged_in_client,
    service_one
):
    service_one['can_send_letters'] = True
    service_one['letter_contact_block'] = 'foo bar baz waz'
    response = logged_in_client.get(url_for('main.service_set_letter_contact_block', service_id=service_one['id']))
    assert response.status_code == 200
    assert 'foo bar baz waz' in response.get_data(as_text=True)


def test_set_letter_contact_block_saves(
    logged_in_client,
    service_one,
    mock_update_service,
):
    service_one['can_send_letters'] = True
    response = logged_in_client.post(
        url_for('main.service_set_letter_contact_block', service_id=service_one['id']),
        data={'letter_contact_block': 'foo bar baz waz'}
    )
    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    mock_update_service.assert_called_once_with(service_one['id'], letter_contact_block='foo bar baz waz')


def test_set_letter_contact_block_redirects_to_template(
    logged_in_client,
    service_one,
    mock_update_service,
):
    service_one['can_send_letters'] = True
    fake_template_id = uuid.uuid4()
    response = logged_in_client.post(
        url_for(
            'main.service_set_letter_contact_block',
            service_id=service_one['id'],
            from_template=fake_template_id,
        ),
        data={'letter_contact_block': ''},
    )
    assert response.status_code == 302
    assert response.location == url_for(
        'main.view_template',
        service_id=service_one['id'],
        template_id=fake_template_id,
        _external=True,
    )


def test_set_letter_contact_block_has_max_10_lines(
    logged_in_client,
    service_one,
    mock_update_service,
):
    service_one['can_send_letters'] = True
    response = logged_in_client.post(
        url_for('main.service_set_letter_contact_block', service_id=service_one['id']),
        data={'letter_contact_block': '\n'.join(map(str, range(0, 11)))}
    )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    error_message = page.find('span', class_='error-message').text.strip()
    assert error_message == 'Contains 11 lines, maximum is 10'


def test_set_letter_branding_platform_admin_only(
    logged_in_client,
    service_one,
):
    response = logged_in_client.get(url_for('main.set_letter_branding', service_id=service_one['id']))
    assert response.status_code == 403


@pytest.mark.parametrize('current_dvla_org_id, expected_selected', [
    (None, '001'),
    ('500', '500'),
])
def test_set_letter_branding_prepopulates(
    logged_in_platform_admin_client,
    service_one,
    mock_get_letter_organisations,
    current_dvla_org_id,
    expected_selected,
):
    if current_dvla_org_id:
        service_one['dvla_organisation'] = current_dvla_org_id
    response = logged_in_platform_admin_client.get(url_for('main.set_letter_branding', service_id=service_one['id']))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.select('input[checked]')[0]['value'] == expected_selected


def test_set_letter_contact_block_saves(
    logged_in_platform_admin_client,
    service_one,
    mock_update_service,
    mock_get_letter_organisations,
):
    response = logged_in_platform_admin_client.post(
        url_for('main.set_letter_branding', service_id=service_one['id']),
        data={'dvla_org_id': '500'}
    )
    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    mock_update_service.assert_called_once_with(service_one['id'], dvla_organisation='500')


def test_should_show_branding(
    logged_in_platform_admin_client,
    service_one,
    mock_get_organisations,
    mock_get_letter_organisations,
):
    response = logged_in_platform_admin_client.get(url_for(
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
    logged_in_platform_admin_client,
    service_one,
    mock_get_organisations
):
    response = logged_in_platform_admin_client.get(url_for(
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
    logged_in_platform_admin_client,
    service_one,
    mock_get_organisations,
    mock_update_service,
):
    response = logged_in_platform_admin_client.post(
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

    mock_get_organisations.assert_called_once_with()
    mock_update_service.assert_called_once_with(
        service_one['id'],
        branding='org',
        organisation='organisation-id'
    )


def test_switch_service_enable_letters(
    logged_in_platform_admin_client,
    service_one,
    mocker,
):
    mocked_fn = mocker.patch('app.service_api_client.update_service_with_properties', return_value=service_one)

    response = logged_in_platform_admin_client.get(
        url_for('main.service_switch_can_send_letters', service_id=service_one['id'])
    )

    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    assert mocked_fn.call_args == call(service_one['id'], {'can_send_letters': True})


def test_switch_service_disable_letters(
    logged_in_platform_admin_client,
    service_one,
    mocker,
):
    service_one['can_send_letters'] = True
    mocked_fn = mocker.patch('app.service_api_client.update_service_with_properties', return_value=service_one)

    response = logged_in_platform_admin_client.get(
        url_for('main.service_switch_can_send_letters', service_id=service_one['id'])
    )

    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    assert mocked_fn.call_args == call(service_one['id'], {"can_send_letters": False})


def test_switch_service_enable_international_sms(
    logged_in_platform_admin_client,
    service_one,
    mocker,
):
    mocked_fn = mocker.patch('app.service_api_client.update_service_with_properties', return_value=service_one)

    response = logged_in_platform_admin_client.get(
        url_for('main.service_switch_can_send_international_sms', service_id=service_one['id'])
    )

    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    assert mocked_fn.call_args == call(service_one['id'], {'can_send_international_sms': True})


def test_switch_service_disable_international_sms(
    logged_in_platform_admin_client,
    service_one,
    mocker,
):
    service_one['can_send_international_sms'] = True
    mocked_fn = mocker.patch('app.service_api_client.update_service_with_properties', return_value=service_one)

    response = logged_in_platform_admin_client.get(
        url_for('main.service_switch_can_send_international_sms', service_id=service_one['id'])
    )

    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    assert mocked_fn.call_args == call(service_one['id'], {"can_send_international_sms": False})


def test_archive_service_after_confirm(
    logged_in_platform_admin_client,
    service_one,
    mocker,
):
    mocked_fn = mocker.patch('app.service_api_client.post', return_value=service_one)

    response = logged_in_platform_admin_client.post(url_for('main.archive_service', service_id=service_one['id']))

    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    assert mocked_fn.call_args == call('/service/{}/archive'.format(service_one['id']), data=None)


def test_archive_service_prompts_user(
    logged_in_platform_admin_client,
    service_one,
    mocker,
    mock_get_letter_organisations,
):
    mocked_fn = mocker.patch('app.service_api_client.post')

    response = logged_in_platform_admin_client.get(url_for('main.archive_service', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Are you sure you want to archive this service?' in page.find('div', class_='banner-dangerous').text
    assert mocked_fn.called is False


def test_cant_archive_inactive_service(
    logged_in_platform_admin_client,
    service_one,
    mock_get_letter_organisations,
):
    service_one['active'] = False

    response = logged_in_platform_admin_client.get(url_for('main.service_settings', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Archive service' not in {a.text for a in page.find_all('a', class_='button')}


def test_suspend_service_after_confirm(
    logged_in_platform_admin_client,
    service_one,
    mocker,
):
    mocked_fn = mocker.patch('app.service_api_client.post', return_value=service_one)

    response = logged_in_platform_admin_client.post(url_for('main.suspend_service', service_id=service_one['id']))

    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    assert mocked_fn.call_args == call('/service/{}/suspend'.format(service_one['id']), data=None)


def test_suspend_service_prompts_user(
    logged_in_platform_admin_client,
    service_one,
    mocker,
    mock_get_letter_organisations,
):
    mocked_fn = mocker.patch('app.service_api_client.post')

    response = logged_in_platform_admin_client.get(url_for('main.suspend_service', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'This will suspend the service and revoke all api keys. Are you sure you want to suspend this service?' in \
           page.find('div', class_='banner-dangerous').text
    assert mocked_fn.called is False


def test_cant_suspend_inactive_service(
    logged_in_platform_admin_client,
    service_one,
    mock_get_letter_organisations,
):
    service_one['active'] = False

    response = logged_in_platform_admin_client.get(url_for('main.service_settings', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Suspend service' not in {a.text for a in page.find_all('a', class_='button')}


def test_resume_service_after_confirm(
    logged_in_platform_admin_client,
    service_one,
    mocker,
):
    service_one['active'] = False
    mocked_fn = mocker.patch('app.service_api_client.post', return_value=service_one)

    response = logged_in_platform_admin_client.post(url_for('main.resume_service', service_id=service_one['id']))

    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    assert mocked_fn.call_args == call('/service/{}/resume'.format(service_one['id']), data=None)


def test_resume_service_prompts_user(
    logged_in_platform_admin_client,
    service_one,
    mocker,
    mock_get_letter_organisations,
):
    service_one['active'] = False
    mocked_fn = mocker.patch('app.service_api_client.post')

    response = logged_in_platform_admin_client.get(url_for('main.resume_service', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'This will resume the service. New api key are required for this service to use the API.' in \
           page.find('div', class_='banner-dangerous').text
    assert mocked_fn.called is False


def test_cant_resume_active_service(
    logged_in_platform_admin_client,
    service_one,
    mock_get_letter_organisations,
):
    response = logged_in_platform_admin_client.get(url_for('main.service_settings', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Resume service' not in {a.text for a in page.find_all('a', class_='button')}


@pytest.mark.parametrize('endpoint, expected_p', [
    (
        'main.service_set_international_sms',
        (
            'Sending text messages to international phone numbers is '
            'an invitation‑only feature.'
        )
    ),
    (
        'main.service_set_letters',
        (
            'Using GOV.UK Notify to send letters is an invitation‑only '
            'feature.'
        )
    ),
])
def test_invitation_pages(
    logged_in_client,
    service_one,
    endpoint,
    expected_p,
):
    response = logged_in_client.get(url_for(endpoint, service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert normalize_spaces(page.select('main p')[0].text) == expected_p
