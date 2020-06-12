from datetime import datetime
from functools import partial
from unittest.mock import ANY, Mock, PropertyMock, call
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError
from notifications_utils.clients.zendesk.zendesk_client import ZendeskClient

import app
from app.utils import email_safe
from tests import (
    find_element_by_tag_and_partial_text,
    invite_json,
    organisation_json,
    sample_uuid,
    service_json,
    validate_route_permission,
)
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
    TEMPLATE_ONE_ID,
    create_active_user_no_api_key_permission,
    create_active_user_no_settings_permission,
    create_active_user_with_permissions,
    create_letter_contact_block,
    create_multiple_email_reply_to_addresses,
    create_multiple_letter_contact_blocks,
    create_multiple_sms_senders,
    create_platform_admin_user,
    create_reply_to_email_address,
    create_sms_sender,
    normalize_spaces,
)

FAKE_TEMPLATE_ID = uuid4()


@pytest.fixture
def mock_get_service_settings_page_common(
    mock_get_all_letter_branding,
    mock_get_inbound_number_for_service,
    mock_get_free_sms_fragment_limit,
    mock_get_service_data_retention,
):
    return


@pytest.mark.parametrize('user, expected_rows', [
    (create_active_user_with_permissions(), [

        'Label Value Action',
        'Service name Test Service Change',
        'Sign-in method Text message code Change',

        'Label Value Action',
        'Send emails On Change',
        'Reply-to email addresses Not set Manage',
        'Email branding GOV.UK Change',
        'Send files by email contact_us@gov.uk Manage',

        'Label Value Action',
        'Send text messages On Change',
        'Text message senders GOVUK Manage',
        'Start text messages with service name On Change',
        'Send international text messages Off Change',
        'Receive text messages Off Change',

        'Label Value Action',
        'Send letters Off Change',

    ]),
    (create_platform_admin_user(), [

        'Label Value Action',
        'Service name Test Service Change',
        'Sign-in method Text message code Change',

        'Label Value Action',
        'Send emails On Change',
        'Reply-to email addresses Not set Manage',
        'Email branding GOV.UK Change',
        'Send files by email contact_us@gov.uk Manage',

        'Label Value Action',
        'Send text messages On Change',
        'Text message senders GOVUK Manage',
        'Start text messages with service name On Change',
        'Send international text messages Off Change',
        'Receive text messages Off Change',

        'Label Value Action',
        'Send letters Off Change',

        'Label Value Action',
        'Live Off Change',
        'Count in list of live services Yes Change',
        'Organisation Test organisation Central government Change',
        'Free text message allowance 250,000 Change',
        'Email branding GOV.UK Change',
        'Letter branding Not set Change',
        'Data retention email Change',
        'Receive inbound SMS Off Change',
        'Email authentication Off Change',
        'Send cell broadcasts Off Change',
    ]),
])
def test_should_show_overview(
        client,
        mocker,
        api_user_active,
        no_reply_to_email_addresses,
        no_letter_contact_blocks,
        mock_get_organisation,
        single_sms_sender,
        user,
        expected_rows,
        mock_get_service_settings_page_common,
):
    service_one = service_json(
        SERVICE_ONE_ID,
        users=[api_user_active['id']],
        permissions=['sms', 'email'],
        organisation_id=ORGANISATION_ID,
        contact_link='contact_us@gov.uk',
    )
    mocker.patch('app.service_api_client.get_service', return_value={'data': service_one})

    client.login(user, mocker, service_one)
    response = client.get(url_for(
        'main.service_settings', service_id=SERVICE_ONE_ID
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('h1').text == 'Settings'
    rows = page.select('tr')
    assert len(rows) == len(expected_rows)
    for index, row in enumerate(expected_rows):
        assert row == " ".join(rows[index].text.split())
    app.service_api_client.get_service.assert_called_with(SERVICE_ONE_ID)


def test_no_go_live_link_for_service_without_organisation(
    client_request,
    mocker,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    platform_admin_user,
    mock_get_service_settings_page_common,
):
    mocker.patch('app.organisations_client.get_organisation', return_value=None)
    client_request.login(platform_admin_user)
    page = client_request.get('main.service_settings', service_id=SERVICE_ONE_ID)

    assert page.find('h1').text == 'Settings'

    is_live = find_element_by_tag_and_partial_text(page, tag='td', string='Live')
    assert normalize_spaces(is_live.find_next_sibling().text) == 'No (organisation must be set first)'

    organisation = find_element_by_tag_and_partial_text(page, tag='td', string='Organisation')
    assert normalize_spaces(organisation.find_next_siblings()[0].text) == 'Not set Central government'
    assert normalize_spaces(organisation.find_next_siblings()[1].text) == 'Change'


def test_organisation_name_links_to_org_dashboard(
    client_request,
    platform_admin_user,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_service_settings_page_common,
    mocker,
    mock_get_organisation,
):
    service_one = service_json(SERVICE_ONE_ID,
                               permissions=['sms', 'email'],
                               organisation_id=ORGANISATION_ID)
    mocker.patch('app.service_api_client.get_service', return_value={'data': service_one})

    client_request.login(platform_admin_user, service_one)
    response = client_request.get(
        'main.service_settings', service_id=SERVICE_ONE_ID
    )

    org_row = find_element_by_tag_and_partial_text(response, tag='tr', string='Organisation')
    assert org_row.find('a')['href'] == url_for('main.organisation_dashboard', org_id=ORGANISATION_ID)
    assert normalize_spaces(org_row.find('a').text) == 'Test organisation'


@pytest.mark.parametrize('service_contact_link,expected_text', [
    ('contact.me@gov.uk', 'Send files by email contact.me@gov.uk Manage'),
    (None, 'Send files by email Not set up Manage'),
])
def test_send_files_by_email_row_on_settings_page(
    client_request,
    platform_admin_user,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_service_settings_page_common,
    mocker,
    mock_get_organisation,
    service_contact_link,
    expected_text
):
    service_one = service_json(
        SERVICE_ONE_ID,
        permissions=['sms', 'email'],
        organisation_id=ORGANISATION_ID,
        contact_link=service_contact_link
    )

    mocker.patch('app.service_api_client.get_service', return_value={'data': service_one})

    client_request.login(platform_admin_user, service_one)
    response = client_request.get(
        'main.service_settings', service_id=SERVICE_ONE_ID
    )

    org_row = find_element_by_tag_and_partial_text(response, tag='tr', string='Send files by email')
    assert normalize_spaces(org_row.get_text()) == expected_text


@pytest.mark.parametrize('permissions, expected_rows', [
    (['email', 'sms', 'inbound_sms', 'international_sms'], [

        'Service name service one Change',
        'Sign-in method Text message code Change',

        'Label Value Action',
        'Send emails On Change',
        'Reply-to email addresses test@example.com Manage',
        'Email branding Organisation name Change',
        'Send files by email Not set up Manage',

        'Label Value Action',
        'Send text messages On Change',
        'Text message senders GOVUK Manage',
        'Start text messages with service name On Change',
        'Send international text messages On Change',
        'Receive text messages On Change',

        'Label Value Action',
        'Send letters Off Change',

    ]),
    (['email', 'sms', 'email_auth'], [

        'Service name service one Change',
        'Sign-in method Email link or text message code Change',

        'Label Value Action',
        'Send emails On Change',
        'Reply-to email addresses test@example.com Manage',
        'Email branding Organisation name Change',
        'Send files by email Not set up Manage',

        'Label Value Action',
        'Send text messages On Change',
        'Text message senders GOVUK Manage',
        'Start text messages with service name On Change',
        'Send international text messages Off Change',
        'Receive text messages Off Change',

        'Label Value Action',
        'Send letters Off Change',

    ]),
    (['letter'], [

        'Service name service one Change',
        'Sign-in method Text message code Change',

        'Label Value Action',
        'Send emails Off Change',

        'Label Value Action',
        'Send text messages Off Change',

        'Label Value Action',
        'Send letters On Change',
        'Sender addresses 1 Example Street Manage',
        'Letter branding Not set Change',

    ]),
    (['broadcast'], [

        'Service name service one Change',
        'Sign-in method Text message code Change',

    ]),
])
def test_should_show_overview_for_service_with_more_things_set(
        client,
        active_user_with_permissions,
        mocker,
        service_one,
        single_reply_to_email_address,
        single_letter_contact_block,
        single_sms_sender,
        mock_get_organisation,
        mock_get_email_branding,
        mock_get_service_settings_page_common,
        permissions,
        expected_rows
):
    client.login(active_user_with_permissions, mocker, service_one)
    service_one['permissions'] = permissions
    service_one['email_branding'] = uuid4()
    response = client.get(url_for(
        'main.service_settings', service_id=service_one['id']
    ))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    for index, row in enumerate(expected_rows):
        assert row == " ".join(page.find_all('tr')[index + 1].text.split())


def test_if_cant_send_letters_then_cant_see_letter_contact_block(
        client_request,
        service_one,
        single_reply_to_email_address,
        no_letter_contact_blocks,
        mock_get_organisation,
        single_sms_sender,
        mock_get_service_settings_page_common,
):
    response = client_request.get('main.service_settings', service_id=service_one['id'])
    assert 'Letter contact block' not in response


def test_letter_contact_block_shows_none_if_not_set(
    client_request,
    service_one,
    single_reply_to_email_address,
    no_letter_contact_blocks,
    mock_get_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    service_one['permissions'] = ['letter']
    page = client_request.get(
        'main.service_settings',
        service_id=SERVICE_ONE_ID,
    )

    div = page.find_all('tr')[9].find_all('td')[1].div
    assert div.text.strip() == 'Not set'
    assert 'default' in div.attrs['class'][0]


def test_escapes_letter_contact_block(
    client_request,
    service_one,
    mocker,
    single_reply_to_email_address,
    single_sms_sender,
    mock_get_organisation,
    injected_letter_contact_block,
    mock_get_service_settings_page_common,
):
    service_one['permissions'] = ['letter']
    page = client_request.get(
        'main.service_settings',
        service_id=SERVICE_ONE_ID,
    )

    div = str(page.find_all('tr')[9].find_all('td')[1].div)
    assert 'foo<br/>bar' in div
    assert '<script>' not in div


def test_should_show_service_name(
    client_request,
):
    page = client_request.get('main.service_name_change', service_id=SERVICE_ONE_ID)
    assert page.find('h1').text == 'Change your service name'
    assert page.find('input', attrs={"type": "text"})['value'] == 'service one'
    assert page.select_one('main p').text == 'Users will see your service name:'
    assert normalize_spaces(page.select_one('main ul').text) == (
        'at the start of every text message '
        'as your email sender name'
    )
    app.service_api_client.get_service.assert_called_with(SERVICE_ONE_ID)


def test_should_show_different_change_service_name_page_for_local_services(
    client_request,
    service_one,
    mocker,
):
    mocker.patch(
        'app.organisations_client.get_organisation_by_domain',
        return_value=organisation_json(organisation_type='local'),
    )
    service_one['organisation_type'] = 'local'
    page = client_request.get('main.service_name_change', service_id=SERVICE_ONE_ID)
    assert page.find('h1').text == 'Change your service name'
    assert page.find('input', attrs={"type": "text"})['value'] == 'service one'
    assert page.select_one('main .govuk-body').text.strip() == (
        'Your service name should tell users what the message is about as well as who it’s from. For example:'
    )
    # when no organisation on the service object, default org for the user is used for hint
    assert "School admissions - Test Org" in page.find_all("ul", class_="govuk-list govuk-list--bullet")[0].text

    app.service_api_client.get_service.assert_called_with(SERVICE_ONE_ID)


def test_should_show_service_org_in_hint_on_change_service_name_page_for_local_services_if_service_has_org(
    client_request,
    service_one,
    mocker,
):
    mocker.patch(
        'app.organisations_client.get_organisation_by_domain',
        return_value=organisation_json(organisation_type='local'),
    )
    mocker.patch('app.organisations_client.get_organisation', return_value=organisation_json(
        organisation_type='local', name="Local Authority")
    )
    service_one['organisation_type'] = 'local'
    service_one['organisation'] = '1234'
    page = client_request.get('main.service_name_change', service_id=SERVICE_ONE_ID)
    # when there is organisation on the service object, it is used for hint text instead of user default org
    assert "School admissions - Local Authority" in page.find_all("ul", class_="govuk-list govuk-list--bullet")[0].text


def test_should_show_service_name_with_no_prefixing(
    client_request,
    service_one,
):
    service_one['prefix_sms'] = False
    page = client_request.get('main.service_name_change', service_id=SERVICE_ONE_ID)
    assert page.find('h1').text == 'Change your service name'
    assert page.select_one('main p').text == 'Users will see your service name as your email sender name.'


def test_should_redirect_after_change_service_name(
    client_request,
    mock_update_service,
    mock_service_name_is_unique,
):
    client_request.post(
        'main.service_name_change',
        service_id=SERVICE_ONE_ID,
        _data={'name': "new name"},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_name_change_confirm',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )

    assert mock_service_name_is_unique.called is True


def test_should_not_hit_api_if_service_name_hasnt_changed(
    client_request,
    mock_update_service,
    mock_service_name_is_unique,
):
    client_request.post(
        'main.service_name_change',
        service_id=SERVICE_ONE_ID,
        _data={'name': 'service one'},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_settings',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    )
    assert not mock_service_name_is_unique.called
    assert not mock_update_service.called


def test_service_name_change_fails_if_new_name_has_less_than_2_alphanumeric_characters(
    client_request,
    mock_update_service,
    mock_service_name_is_unique,
):
    page = client_request.post(
        'main.service_name_change',
        service_id=SERVICE_ONE_ID,
        _data={'name': "."},
        _expected_status=200,
    )
    assert not mock_service_name_is_unique.called
    assert not mock_update_service.called
    assert page.find("span", {"class": "error-message"})


@pytest.mark.parametrize('user, expected_text, expected_link', [
    (
        create_active_user_with_permissions(),
        'To remove these restrictions, you can send us a request to go live.',
        True,
    ),
    (
        create_active_user_no_settings_permission(),
        'Your service manager can ask to have these restrictions removed.',
        False,
    ),
])
def test_show_restricted_service(
    client_request,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common,
    user,
    expected_text,
    expected_link,
):
    client_request.login(user)
    page = client_request.get(
        'main.service_settings',
        service_id=SERVICE_ONE_ID,
    )

    assert page.find('h1').text == 'Settings'
    assert page.select('main h2')[0].text == 'Your service is in trial mode'

    request_to_live = page.select('main p')[1]
    request_to_live_link = request_to_live.select_one('a')
    assert normalize_spaces(request_to_live.text) == expected_text

    if expected_link:
        assert request_to_live_link.text.strip() == 'request to go live'
        assert request_to_live_link['href'] == url_for('main.request_to_go_live', service_id=SERVICE_ONE_ID)
    else:
        assert not request_to_live_link


def test_show_restricted_broadcast_service(
    client_request,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    service_one['permissions'] = 'broadcast'
    page = client_request.get(
        'main.service_settings',
        service_id=SERVICE_ONE_ID,
    )

    assert page.select('main h2')[0].text == 'Your service is in trial mode'

    request_to_live = page.select_one('main p')
    request_to_live_link = request_to_live.select_one('a')
    assert normalize_spaces(page.select_one('main p').text) == (
        'To remove these restrictions, you can send us a request to go live.'
    )
    assert request_to_live_link['href'] == url_for('main.request_to_go_live', service_id=SERVICE_ONE_ID)
    assert not page.select_one('main ul')


@freeze_time("2017-04-01 11:09:00.061258")
def test_switch_service_to_live(
    client_request,
    platform_admin_user,
    mock_update_service,
    mock_get_inbound_number_for_service
):
    client_request.login(platform_admin_user)
    client_request.post(
        'main.service_switch_live',
        service_id=SERVICE_ONE_ID,
        _data={'enabled': 'True'},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_settings',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )
    mock_update_service.assert_called_with(
        SERVICE_ONE_ID,
        message_limit=250000,
        restricted=False,
        go_live_at="2017-04-01 11:09:00.061258"
    )


def test_show_live_service(
    client_request,
    mock_get_live_service,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    page = client_request.get(
        'main.service_settings',
        service_id=SERVICE_ONE_ID,
    )
    assert page.find('h1').text.strip() == 'Settings'
    assert 'Your service is in trial mode' not in page.text


def test_switch_service_to_restricted(
    client_request,
    platform_admin_user,
    mock_get_live_service,
    mock_update_service,
    mock_get_inbound_number_for_service,
):
    client_request.login(platform_admin_user)
    client_request.post(
        'main.service_switch_live',
        service_id=SERVICE_ONE_ID,
        _data={'enabled': 'False'},
        _expected_status=302,
        _expected_response=url_for(
            'main.service_settings',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )
    mock_update_service.assert_called_with(
        SERVICE_ONE_ID,
        message_limit=50,
        restricted=True,
        go_live_at=None
    )


@pytest.mark.parametrize('count_as_live, selected, labelled', (
    (True, 'True', 'Yes'),
    (False, 'False', 'No'),
))
def test_show_switch_service_to_count_as_live_page(
    mocker,
    client_request,
    platform_admin_user,
    mock_update_service,
    count_as_live,
    selected,
    labelled,
):
    mocker.patch(
        'app.models.service.Service.count_as_live',
        create=True,
        new_callable=PropertyMock,
        return_value=count_as_live,
    )
    client_request.login(platform_admin_user)
    page = client_request.get(
        'main.service_switch_count_as_live',
        service_id=SERVICE_ONE_ID,
    )
    assert page.select_one('[checked]')['value'] == selected
    assert page.select_one('label[for={}]'.format(
        page.select_one('[checked]')['id']
    )).text.strip() == labelled


@pytest.mark.parametrize('post_data, expected_persisted_value', (
    ('True', True),
    ('False', False),
))
def test_switch_service_to_count_as_live(
    client_request,
    platform_admin_user,
    mock_update_service,
    post_data,
    expected_persisted_value,
):
    client_request.login(platform_admin_user)
    client_request.post(
        'main.service_switch_count_as_live',
        service_id=SERVICE_ONE_ID,
        _data={'enabled': post_data},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_settings',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )
    mock_update_service.assert_called_with(
        SERVICE_ONE_ID,
        count_as_live=expected_persisted_value,
    )


def test_should_not_allow_duplicate_names(
    client_request,
    mock_service_name_is_not_unique,
    service_one,
):
    page = client_request.post(
        'main.service_name_change',
        service_id=SERVICE_ONE_ID,
        _data={'name': "SErvICE TWO"},
        _expected_status=200,
    )

    assert 'This service name is already in use' in page.text
    app.service_api_client.is_service_name_unique.assert_called_once_with(
        SERVICE_ONE_ID,
        'SErvICE TWO',
        'service.two',
    )


def test_should_show_service_name_confirmation(
    client_request,
):
    service_new_name = 'New Name'
    with client_request.session_transaction() as session:
        session['service_name_change'] = service_new_name
    page = client_request.get(
        'main.service_name_change_confirm',
        service_id=SERVICE_ONE_ID,
    )
    assert 'Change your service name' in page.text
    app.service_api_client.get_service.assert_called_with(SERVICE_ONE_ID)


def test_should_redirect_after_service_name_confirmation(
    client_request,
    mock_update_service,
    mock_verify_password,
    mock_get_inbound_number_for_service,
):
    service_new_name = 'New Name'
    with client_request.session_transaction() as session:
        session['service_name_change'] = service_new_name
    client_request.post(
        'main.service_name_change_confirm',
        service_id=SERVICE_ONE_ID,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_settings',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        name=service_new_name,
        email_from=email_safe(service_new_name)
    )
    assert mock_verify_password.called is True


def test_should_raise_duplicate_name_handled(
    client_request,
    mock_update_service_raise_httperror_duplicate_name,
    mock_verify_password,
):
    with client_request.session_transaction() as session:
        session['service_name_change'] = 'New Name'

    client_request.post(
        'main.service_name_change_confirm',
        service_id=SERVICE_ONE_ID,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_name_change',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    )

    assert mock_update_service_raise_httperror_duplicate_name.called
    assert mock_verify_password.called


def test_service_name_change_confirm_handles_expired_session(
    client_request, mock_verify_password, mock_update_service
):
    page = client_request.post(
        'main.service_name_change_confirm',
        service_id=SERVICE_ONE_ID,
        _follow_redirects=True
    )
    mock_verify_password.assert_not_called()
    mock_update_service.assert_not_called()

    assert page.find('div', 'banner-dangerous').text.strip() == "The change you made was not saved. Please try again."


@pytest.mark.parametrize('volumes, consent_to_research, expected_estimated_volumes_item', [
    ((0, 0, 0), None, 'Tell us how many messages you expect to send Not completed'),
    ((1, 0, 0), None, 'Tell us how many messages you expect to send Not completed'),
    ((1, 0, 0), False, 'Tell us how many messages you expect to send Completed'),
    ((1, 0, 0), True, 'Tell us how many messages you expect to send Completed'),
    ((9, 99, 999), True, 'Tell us how many messages you expect to send Completed'),
])
def test_should_check_if_estimated_volumes_provided(
    client_request,
    mocker,
    single_sms_sender,
    single_reply_to_email_address,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_get_organisation,
    mock_get_invites_for_service,
    volumes,
    consent_to_research,
    expected_estimated_volumes_item,
):

    for volume, channel in zip(volumes, ('sms', 'email', 'letter')):
        mocker.patch(
            'app.models.service.Service.volume_{}'.format(channel),
            create=True,
            new_callable=PropertyMock,
            return_value=volume,
        )

    mocker.patch(
        'app.models.service.Service.consent_to_research',
        create=True,
        new_callable=PropertyMock,
        return_value=consent_to_research,
    )

    page = client_request.get(
        'main.request_to_go_live', service_id=SERVICE_ONE_ID
    )
    assert page.h1.text == 'Before you request to go live'

    assert normalize_spaces(
        page.select_one('.task-list .task-list-item').text
    ) == (
        expected_estimated_volumes_item
    )


@pytest.mark.parametrize((
    'count_of_users_with_manage_service,'
    'count_of_invites_with_manage_service,'
    'expected_user_checklist_item'
), [
    (1, 0, 'Add a team member who can manage settings, team and usage Not completed'),
    (2, 0, 'Add a team member who can manage settings, team and usage Completed'),
    (1, 1, 'Add a team member who can manage settings, team and usage Completed'),
])
@pytest.mark.parametrize('count_of_templates, expected_templates_checklist_item', [
    (0, 'Add templates with examples of the content you plan to send Not completed'),
    (1, 'Add templates with examples of the content you plan to send Completed'),
    (2, 'Add templates with examples of the content you plan to send Completed'),
])
@pytest.mark.parametrize((
    'volume_email,'
    'count_of_email_templates,'
    'reply_to_email_addresses,'
    'expected_reply_to_checklist_item'
), [
    pytest.param(None, 0, [], '', marks=pytest.mark.xfail(raises=IndexError)),
    pytest.param(0, 0, [], '', marks=pytest.mark.xfail(raises=IndexError)),
    (None, 1, [], 'Add a reply-to email address Not completed'),
    (None, 1, [{}], 'Add a reply-to email address Completed'),
    (1, 1, [], 'Add a reply-to email address Not completed'),
    (1, 1, [{}], 'Add a reply-to email address Completed'),
    (1, 0, [], 'Add a reply-to email address Not completed'),
    (1, 0, [{}], 'Add a reply-to email address Completed'),
])
def test_should_check_for_sending_things_right(
    client_request,
    mocker,
    service_one,
    fake_uuid,
    single_sms_sender,
    count_of_users_with_manage_service,
    count_of_invites_with_manage_service,
    expected_user_checklist_item,
    count_of_templates,
    expected_templates_checklist_item,
    volume_email,
    count_of_email_templates,
    reply_to_email_addresses,
    expected_reply_to_checklist_item,
    active_user_with_permissions,
    active_user_no_settings_permission,
):
    def _templates_by_type(template_type):
        return {
            'email': list(range(0, count_of_email_templates)),
            'sms': [],
        }.get(template_type)
    active_user_with_permissions,
    mock_get_users = mocker.patch(
        'app.models.user.Users.client_method',
        return_value=(
            [active_user_with_permissions] * count_of_users_with_manage_service +
            [active_user_no_settings_permission]
        )
    )
    invite_one = invite_json(id_=uuid4(),
                             from_user=service_one['users'][0],
                             service_id=service_one['id'],
                             email_address='invited_user@test.gov.uk',
                             permissions='view_activity,send_messages,manage_service,manage_api_keys',
                             created_at=datetime.utcnow(),
                             status='pending',
                             auth_type='sms_auth',
                             folder_permissions=[])

    invite_two = invite_one.copy()
    invite_two['permissions'] = 'view_activity'

    mock_get_invites = mocker.patch(
        'app.models.user.InvitedUsers.client_method',
        return_value=(
            ([invite_one] * count_of_invites_with_manage_service) +
            [invite_two]
        )
    )

    mock_templates = mocker.patch(
        'app.models.service.Service.all_templates',
        new_callable=PropertyMock,
        return_value=list(range(0, count_of_templates)),
    )

    mocker.patch(
        'app.models.service.Service.get_templates',
        side_effect=_templates_by_type,
    )
    mocker.patch(
        'app.models.service.Service.organisation_id',
        new_callable=PropertyMock,
        return_value=None,
    )

    mock_get_reply_to_email_addresses = mocker.patch(
        'app.main.views.service_settings.service_api_client.get_reply_to_email_addresses',
        return_value=reply_to_email_addresses
    )

    for channel, volume in (('email', volume_email), ('sms', 0), ('letter', 1)):
        mocker.patch(
            'app.models.service.Service.volume_{}'.format(channel),
            create=True,
            new_callable=PropertyMock,
            return_value=volume,
        )

    page = client_request.get(
        'main.request_to_go_live', service_id=SERVICE_ONE_ID
    )
    assert page.h1.text == 'Before you request to go live'

    checklist_items = page.select('.task-list .task-list-item')
    assert normalize_spaces(checklist_items[1].text) == expected_user_checklist_item
    assert normalize_spaces(checklist_items[2].text) == expected_templates_checklist_item
    assert normalize_spaces(checklist_items[3].text) == expected_reply_to_checklist_item

    mock_get_users.assert_called_once_with(SERVICE_ONE_ID)
    mock_get_invites.assert_called_once_with(SERVICE_ONE_ID)
    assert mock_templates.called is True

    if count_of_email_templates:
        mock_get_reply_to_email_addresses.assert_called_once_with(SERVICE_ONE_ID)


@pytest.mark.parametrize('checklist_completed, agreement_signed, expected_button', (
    (True, True, True),
    (True, None, True),
    (True, False, False),
    (False, True, False),
    (False, None, False),
))
def test_should_not_show_go_live_button_if_checklist_not_complete(
    client_request,
    mocker,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_get_service_organisation,
    mock_get_invites_for_service,
    single_sms_sender,
    checklist_completed,
    agreement_signed,
    expected_button,
):
    mocker.patch(
        'app.models.service.Service.go_live_checklist_completed',
        new_callable=PropertyMock,
        return_value=checklist_completed,
    )
    mocker.patch(
        'app.models.organisation.Organisation.agreement_signed',
        new_callable=PropertyMock,
        return_value=agreement_signed,
        create=True,
    )

    for channel in ('email', 'sms', 'letter'):
        mocker.patch(
            'app.models.service.Service.volume_{}'.format(channel),
            create=True,
            new_callable=PropertyMock,
            return_value=0,
        )

    page = client_request.get(
        'main.request_to_go_live', service_id=SERVICE_ONE_ID
    )
    assert page.h1.text == 'Before you request to go live'

    if expected_button:
        assert page.select_one('form')['method'] == 'post'
        assert 'action' not in page.select_one('form')
        assert normalize_spaces(page.select('main p')[0].text) == (
            'When we receive your request we’ll get back to you within one working day.'
        )
        assert normalize_spaces(page.select('main p')[1].text) == (
            'By requesting to go live you’re agreeing to our terms of use.'
        )
        page.select_one('[type=submit]').text.strip() == ('Request to go live')
    else:
        assert not page.select('form')
        assert not page.select('main [type=submit]')
        assert len(page.select('main p')) == 1
        assert normalize_spaces(page.select_one('main p').text) == (
            'You must complete these steps before you can request to go live.'
        )


@pytest.mark.parametrize((
    'estimated_sms_volume,'
    'organisation_type,'
    'count_of_sms_templates,'
    'sms_senders,'
    'expected_sms_sender_checklist_item'
), [
    pytest.param(
        0,
        'local',
        0,
        [],
        '',
        marks=pytest.mark.xfail(raises=IndexError)
    ),
    pytest.param(
        None,
        'local',
        0,
        [{'is_default': True, 'sms_sender': 'GOVUK'}],
        '',
        marks=pytest.mark.xfail(raises=IndexError)
    ),
    pytest.param(
        1,
        'central',
        99,
        [{'is_default': True, 'sms_sender': 'GOVUK'}],
        '',
        marks=pytest.mark.xfail(raises=IndexError)
    ),
    pytest.param(
        None,
        'central',
        99,
        [{'is_default': True, 'sms_sender': 'GOVUK'}],
        '',
        marks=pytest.mark.xfail(raises=IndexError)
    ),
    pytest.param(
        1,
        'central',
        99,
        [{'is_default': True, 'sms_sender': 'GOVUK'}],
        '',
        marks=pytest.mark.xfail(raises=IndexError)
    ),
    (
        None,
        'local',
        1,
        [],
        'Change your text message sender name Not completed',
    ),
    (
        1,
        'nhs_local',
        0,
        [],
        'Change your text message sender name Not completed',
    ),
    (
        None,
        'school_or_college',
        1,
        [{'is_default': True, 'sms_sender': 'GOVUK'}],
        'Change your text message sender name Not completed',
    ),
    (
        None,
        'local',
        1,
        [
            {'is_default': False, 'sms_sender': 'GOVUK'},
            {'is_default': True, 'sms_sender': 'KUVOG'},
        ],
        'Change your text message sender name Completed',
    ),
    (
        None,
        'nhs_local',
        1,
        [{'is_default': True, 'sms_sender': 'KUVOG'}],
        'Change your text message sender name Completed',
    ),
])
def test_should_check_for_sms_sender_on_go_live(
    client_request,
    service_one,
    mocker,
    mock_get_organisation,
    mock_get_invites_for_service,
    organisation_type,
    count_of_sms_templates,
    sms_senders,
    expected_sms_sender_checklist_item,
    estimated_sms_volume,
):
    service_one['organisation_type'] = organisation_type

    def _templates_by_type(template_type):
        return list(range(0, {
            'email': 0,
            'sms': count_of_sms_templates,
        }.get(template_type, count_of_sms_templates)))

    mocker.patch(
        'app.models.service.Service.has_team_members',
        return_value=True,
    )
    mock_templates = mocker.patch(
        'app.models.service.Service.all_templates',
        new_callable=PropertyMock,
        side_effect=partial(_templates_by_type, 'all'),
    )
    mocker.patch(
        'app.models.service.Service.get_templates',
        side_effect=_templates_by_type,
    )

    mock_get_sms_senders = mocker.patch(
        'app.main.views.service_settings.service_api_client.get_sms_senders',
        return_value=sms_senders,
    )
    mocker.patch(
        'app.main.views.service_settings.service_api_client.get_reply_to_email_addresses',
        return_value=[],
    )

    for channel, volume in (('email', 0), ('sms', estimated_sms_volume)):
        mocker.patch(
            'app.models.service.Service.volume_{}'.format(channel),
            create=True,
            new_callable=PropertyMock,
            return_value=volume,
        )

    page = client_request.get(
        'main.request_to_go_live', service_id=SERVICE_ONE_ID
    )
    assert page.h1.text == 'Before you request to go live'

    checklist_items = page.select('.task-list .task-list-item')
    assert normalize_spaces(checklist_items[3].text) == expected_sms_sender_checklist_item

    assert mock_templates.called is True

    mock_get_sms_senders.assert_called_once_with(SERVICE_ONE_ID)


@pytest.mark.parametrize('agreement_signed, expected_item', (
    pytest.param(
        None,
        '',
        marks=pytest.mark.xfail(raises=IndexError)
    ),
    (
        True,
        'Accept our data sharing and financial agreement Completed',
    ),
    (
        False,
        'Accept our data sharing and financial agreement Not completed',
    ),
))
def test_should_check_for_mou_on_request_to_go_live(
    client_request,
    service_one,
    mocker,
    agreement_signed,
    mock_get_invites_for_service,
    mock_get_service_organisation,
    expected_item,
):
    mocker.patch(
        'app.models.service.Service.has_team_members',
        return_value=False,
    )
    mocker.patch(
        'app.models.service.Service.all_templates',
        new_callable=PropertyMock,
        return_value=[],
    )
    mocker.patch(
        'app.main.views.service_settings.service_api_client.get_sms_senders',
        return_value=[],
    )
    mocker.patch(
        'app.main.views.service_settings.service_api_client.get_reply_to_email_addresses',
        return_value=[],
    )
    for channel in {'email', 'sms', 'letter'}:
        mocker.patch(
            'app.models.service.Service.volume_{}'.format(channel),
            create=True,
            new_callable=PropertyMock,
            return_value=None,
        )

    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(agreement_signed=agreement_signed)
    )
    page = client_request.get(
        'main.request_to_go_live', service_id=SERVICE_ONE_ID
    )
    assert page.h1.text == 'Before you request to go live'

    checklist_items = page.select('.task-list .task-list-item')
    assert normalize_spaces(checklist_items[3].text) == expected_item


@pytest.mark.parametrize('organisation_type', (
    'nhs_gp',
    pytest.param(
        'central',
        marks=pytest.mark.xfail(raises=IndexError)
    ),
))
def test_gp_without_organisation_is_shown_agreement_step(
    client_request,
    service_one,
    mocker,
    organisation_type,
):
    mocker.patch(
        'app.models.service.Service.has_team_members',
        return_value=False,
    )
    mocker.patch(
        'app.models.service.Service.all_templates',
        new_callable=PropertyMock,
        return_value=[],
    )
    mocker.patch(
        'app.main.views.service_settings.service_api_client.get_sms_senders',
        return_value=[],
    )
    mocker.patch(
        'app.main.views.service_settings.service_api_client.get_reply_to_email_addresses',
        return_value=[],
    )
    for channel in {'email', 'sms', 'letter'}:
        mocker.patch(
            'app.models.service.Service.volume_{}'.format(channel),
            create=True,
            new_callable=PropertyMock,
            return_value=None,
        )
    mocker.patch(
        'app.models.service.Service.organisation_id',
        new_callable=PropertyMock,
        return_value=None,
    )
    mocker.patch(
        'app.models.service.Service.organisation_type',
        new_callable=PropertyMock,
        return_value=organisation_type,
    )

    page = client_request.get(
        'main.request_to_go_live', service_id=SERVICE_ONE_ID
    )
    assert page.h1.text == 'Before you request to go live'
    assert normalize_spaces(
        page.select('.task-list .task-list-item')[3].text
    ) == (
        'Accept our data sharing and financial agreement Not completed'
    )


def test_non_gov_user_is_told_they_cant_go_live(
    client_request,
    api_nongov_user_active,
    mock_get_invites_for_service,
    mocker,
    mock_get_organisations,
    mock_get_organisation,
):
    mocker.patch(
        'app.models.service.Service.has_team_members',
        return_value=False,
    )
    mocker.patch(
        'app.models.service.Service.all_templates',
        new_callable=PropertyMock,
        return_value=[],
    )
    mocker.patch(
        'app.main.views.service_settings.service_api_client.get_sms_senders',
        return_value=[],
    )
    mocker.patch(
        'app.main.views.service_settings.service_api_client.get_reply_to_email_addresses',
        return_value=[],
    )
    client_request.login(api_nongov_user_active)
    page = client_request.get(
        'main.request_to_go_live', service_id=SERVICE_ONE_ID
    )
    assert normalize_spaces(page.select_one('main p').text) == (
        'Only team members with a government email address can request to go live.'
    )
    assert len(page.select('main form')) == 0
    assert len(page.select('main button')) == 0


@pytest.mark.parametrize('consent_to_research, displayed_consent', (
    (None, None),
    (True, 'yes'),
    (False, 'no'),
))
@pytest.mark.parametrize('volumes, displayed_volumes', (
    (
        (('email', None), ('sms', None), ('letter', None)),
        ('', '', ''),
    ),
    (
        (('email', 1234), ('sms', 0), ('letter', 999)),
        ('1,234', '0', '999'),
    ),
))
def test_should_show_estimate_volumes(
    mocker,
    client_request,
    volumes,
    displayed_volumes,
    consent_to_research,
    displayed_consent,
):
    for channel, volume in volumes:
        mocker.patch(
            'app.models.service.Service.volume_{}'.format(channel),
            create=True,
            new_callable=PropertyMock,
            return_value=volume,
        )
    mocker.patch(
        'app.models.service.Service.consent_to_research',
        create=True,
        new_callable=PropertyMock,
        return_value=consent_to_research,
    )
    page = client_request.get(
        'main.estimate_usage', service_id=SERVICE_ONE_ID
    )
    assert page.h1.text == 'Tell us how many messages you expect to send'
    for channel, label, value in (
        (
            'email',
            'How many emails do you expect to send in the next year? For example, 50,000',
            displayed_volumes[0],
        ),
        (
            'sms',
            'How many text messages do you expect to send in the next year? For example, 50,000',
            displayed_volumes[1],
        ),
        (
            'letter',
            'How many letters do you expect to send in the next year? For example, 50,000',
            displayed_volumes[2],
        ),
    ):
        assert normalize_spaces(
            page.select_one('label[for=volume_{}]'.format(channel)).text
        ) == label
        assert page.select_one('#volume_{}'.format(channel))['value'] == value

    assert len(page.select('input[type=radio]')) == 2

    if displayed_consent is None:
        assert len(page.select('input[checked]')) == 0
    else:
        assert len(page.select('input[checked]')) == 1
        assert page.select_one('input[checked]')['value'] == displayed_consent


@pytest.mark.parametrize('consent_to_research, expected_persisted_consent_to_research', (
    ('yes', True),
    ('no', False),
))
def test_should_show_persist_estimated_volumes(
    client_request,
    mock_update_service,
    consent_to_research,
    expected_persisted_consent_to_research,
):
    client_request.post(
        'main.estimate_usage',
        service_id=SERVICE_ONE_ID,
        _data={
            'volume_email': '1,234,567',
            'volume_sms': '',
            'volume_letter': '098',
            'consent_to_research': consent_to_research,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            'main.request_to_go_live',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )
    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        volume_email=1234567,
        volume_sms=0,
        volume_letter=98,
        consent_to_research=expected_persisted_consent_to_research,
    )


@pytest.mark.parametrize('data, error_selector, expected_error_message', (
    (
        {
            'volume_email': '1234',
            'volume_sms': '2000000001',
            'volume_letter': '9876',
            'consent_to_research': 'yes',
        },
        'label[for=volume_sms]',
        (
            'How many text messages do you expect to send in the next year? For example, 50,000 '
            'Number of text messages must be 2,000,000,000 or less'
        )
    ),
    (
        {
            'volume_email': '1 234',
            'volume_sms': '0',
            'volume_letter': '9876',
            'consent_to_research': '',
        },
        '[data-error-label="consent_to_research"]',
        'Select yes or no'
    ),
))
def test_should_error_if_bad_estimations_given(
    client_request,
    mock_update_service,
    data,
    error_selector,
    expected_error_message,
):
    page = client_request.post(
        'main.estimate_usage',
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one(error_selector).text) == expected_error_message
    assert mock_update_service.called is False


def test_should_error_if_all_volumes_zero(
    client_request,
    mock_update_service,
):
    page = client_request.post(
        'main.estimate_usage',
        service_id=SERVICE_ONE_ID,
        _data={
            'volume_email': '',
            'volume_sms': '0',
            'volume_letter': '0,00 0',
            'consent_to_research': 'yes',
        },
        _expected_status=200,
    )
    assert page.select('input[type=text]')[0]['value'] == ''
    assert page.select('input[type=text]')[1]['value'] == '0'
    assert page.select('input[type=text]')[2]['value'] == '0,00 0'
    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        'Enter the number of messages you expect to send in the next year'
    )
    assert mock_update_service.called is False


def test_should_not_default_to_zero_if_some_fields_dont_validate(
    client_request,
    mock_update_service,
):
    page = client_request.post(
        'main.estimate_usage',
        service_id=SERVICE_ONE_ID,
        _data={
            'volume_email': '1234',
            'volume_sms': '',
            'volume_letter': 'aaaaaaaaaaaaa',
            'consent_to_research': 'yes',
        },
        _expected_status=200,
    )
    assert page.select('input[type=text]')[0]['value'] == '1234'
    assert page.select('input[type=text]')[1]['value'] == ''
    assert page.select('input[type=text]')[2]['value'] == 'aaaaaaaaaaaaa'
    assert normalize_spaces(
        page.select_one('label[for=volume_letter]').text
    ) == (
        'How many letters do you expect to send in the next year? '
        'For example, 50,000 '
        'Enter the number of letters you expect to send'
    )
    assert mock_update_service.called is False


def test_non_gov_users_cant_request_to_go_live(
    client_request,
    api_nongov_user_active,
    mock_get_organisations,
):
    client_request.login(api_nongov_user_active)
    client_request.post(
        'main.request_to_go_live',
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


@pytest.mark.parametrize('volumes, displayed_volumes, formatted_displayed_volumes, extra_tags', (
    (
        (('email', None), ('sms', None), ('letter', None)),
        ', , ',
        (
            'Emails in next year: \n'
            'Text messages in next year: \n'
            'Letters in next year: \n'
        ),
        ['notify_go_live_incomplete_volumes']
    ),
    (
        (('email', 1234), ('sms', 0), ('letter', 999)),
        '0, 1234, 999',  # This is a different order to match the spreadsheet
        (
            'Emails in next year: 1,234\n'
            'Text messages in next year: 0\n'
            'Letters in next year: 999\n'
        ),
        [],
    ),
))
@freeze_time("2012-12-21 13:12:12.12354")
def test_should_redirect_after_request_to_go_live(
    client_request,
    mocker,
    active_user_with_permissions,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisations_and_services_for_user,
    single_sms_sender,
    mock_get_service_settings_page_common,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_update_service,
    mock_get_invites_without_manage_permission,
    volumes,
    displayed_volumes,
    formatted_displayed_volumes,
    extra_tags,
):
    for channel, volume in volumes:
        mocker.patch(
            'app.models.service.Service.volume_{}'.format(channel),
            create=True,
            new_callable=PropertyMock,
            return_value=volume,
        )
    mock_post = mocker.patch('app.main.views.service_settings.zendesk_client.create_ticket', autospec=True)
    page = client_request.post(
        'main.request_to_go_live',
        service_id=SERVICE_ONE_ID,
        _follow_redirects=True
    )
    mock_post.assert_called_with(
        subject='Request to go live - service one',
        message=ANY,
        ticket_type=ZendeskClient.TYPE_QUESTION,
        user_name=active_user_with_permissions['name'],
        user_email=active_user_with_permissions['email_address'],
        tags=[
            'notify_action',
            'notify_go_live',
        ] + extra_tags + [
            'notify_go_live_incomplete_checklist',
            'notify_go_live_incomplete_mou',
            'notify_go_live_incomplete_team_member',
        ],
    )
    assert mock_post.call_args[1]['message'] == (
        'Service: service one\n'
        'http://localhost/services/{service_id}\n'
        '\n'
        '---\n'
        'Organisation type: Central\n'
        'Agreement signed: Can’t tell (domain is user.gov.uk).\n'
        '{formatted_displayed_volumes}'
        'Consent to research: Yes\n'
        'Other live services: No\n'
        '\n'
        '---\n'
        'Request sent by test@user.gov.uk\n'
    ).format(
        service_id=SERVICE_ONE_ID,
        displayed_volumes=displayed_volumes,
        formatted_displayed_volumes=formatted_displayed_volumes,
    )

    assert normalize_spaces(page.select_one('.banner-default').text) == (
        'Thanks for your request to go live. We’ll get back to you within one working day.'
    )
    assert normalize_spaces(page.select_one('h1').text) == (
        'Settings'
    )
    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        go_live_user=active_user_with_permissions['id']
    )


def test_request_to_go_live_displays_go_live_notes_in_zendesk_ticket(
    client_request,
    mocker,
    active_user_with_permissions,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisations_and_services_for_user,
    single_sms_sender,
    mock_get_service_organisation,
    mock_get_service_settings_page_common,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_update_service,
    mock_get_invites_without_manage_permission,
):
    go_live_note = 'This service is not allowed to go live'

    mocker.patch(
        'app.organisations_client.get_organisation',
        side_effect=lambda org_id: organisation_json(
            ORGANISATION_ID,
            'Org 1',
            request_to_go_live_notes=go_live_note,
        )
    )
    mock_post = mocker.patch('app.main.views.service_settings.zendesk_client.create_ticket', autospec=True)
    client_request.post(
        'main.request_to_go_live',
        service_id=SERVICE_ONE_ID,
        _follow_redirects=True
    )

    assert mock_post.call_args[1]['message'] == (
        'Service: service one\n'
        'http://localhost/services/{service_id}\n'
        '\n'
        '---\n'
        'Organisation type: Central\n'
        'Agreement signed: No (organisation is Org 1, a crown body). {go_live_note}\n'
        'Emails in next year: 111,111\n'
        'Text messages in next year: 222,222\n'
        'Letters in next year: 333,333\n'
        'Consent to research: Yes\n'
        'Other live services: No\n'
        '\n'
        '---\n'
        'Request sent by test@user.gov.uk\n'
    ).format(
        service_id=SERVICE_ONE_ID,
        go_live_note=go_live_note
    )


def test_should_be_able_to_request_to_go_live_with_no_organisation(
    client_request,
    mocker,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisations_and_services_for_user,
    single_sms_sender,
    mock_get_service_settings_page_common,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_update_service,
    mock_get_invites_without_manage_permission,
):
    for channel in {'email', 'sms', 'letter'}:
        mocker.patch(
            'app.models.service.Service.volume_{}'.format(channel),
            create=True,
            new_callable=PropertyMock,
            return_value=1,
        )
    mock_post = mocker.patch('app.main.views.service_settings.zendesk_client.create_ticket', autospec=True)

    client_request.post(
        'main.request_to_go_live',
        service_id=SERVICE_ONE_ID,
        _follow_redirects=True
    )

    assert mock_post.called is True


@pytest.mark.parametrize(
    (
        'has_team_members,'
        'has_templates,'
        'has_email_templates,'
        'has_sms_templates,'
        'has_email_reply_to_address,'
        'shouldnt_use_govuk_as_sms_sender,'
        'sms_sender_is_govuk,'
        'volume_email,'
        'volume_sms,'
        'volume_letter,'
        'expected_readyness,'
        'agreement_signed,'
        'expected_tags,'
    ),
    (
        (  # Just sending email
            True,
            True,
            True,
            False,
            True,
            True,
            True,
            1, 0, 0,
            'Yes',
            True,
            [
                'notify_action',
                'notify_go_live',
                'notify_go_live_complete',
            ],
        ),
        (  # Needs to set reply to address
            True,
            True,
            True,
            False,
            False,
            True,
            True,
            1, 0, 1,
            'No',
            True,
            [
                'notify_action',
                'notify_go_live',
                'notify_go_live_incomplete_checklist',
                'notify_go_live_incomplete_email_reply_to',
            ],
        ),
        (  # Just sending SMS
            True,
            True,
            False,
            True,
            True,
            True,
            False,
            0, 1, 0,
            'Yes',
            True,
            [
                'notify_action',
                'notify_go_live',
                'notify_go_live_complete',
            ],
        ),
        (  # Needs to change SMS sender
            True,
            True,
            False,
            True,
            True,
            True,
            True,
            0, 1, 0,
            'No',
            True,
            [
                'notify_action',
                'notify_go_live',
                'notify_go_live_incomplete_checklist',
                'notify_go_live_incomplete_sms_sender',
            ],
        ),
        (  # Needs team members
            False,
            True,
            False,
            True,
            True,
            True,
            False,
            1, 0, 0,
            'No',
            True,
            [
                'notify_action',
                'notify_go_live',
                'notify_go_live_incomplete_checklist',
                'notify_go_live_incomplete_team_member',
            ],
        ),
        (  # Needs templates
            True,
            False,
            False,
            True,
            True,
            True,
            False,
            0, 1, 0,
            'No',
            True,
            [
                'notify_action',
                'notify_go_live',
                'notify_go_live_incomplete_checklist',
                'notify_go_live_incomplete_template_content',
            ],
        ),
        (  # Not done anything yet
            False,
            False,
            False,
            False,
            False,
            False,
            True,
            None, None, None,
            'No',
            False,
            [
                'notify_action',
                'notify_go_live',
                'notify_go_live_incomplete_volumes',
                'notify_go_live_incomplete_checklist',
                'notify_go_live_incomplete_mou',
                'notify_go_live_incomplete_team_member',
                'notify_go_live_incomplete_template_content',
            ],
        ),
    ),
)
def test_ready_to_go_live(
    client_request,
    mocker,
    mock_get_service_organisation,
    has_team_members,
    has_templates,
    has_email_templates,
    has_sms_templates,
    has_email_reply_to_address,
    shouldnt_use_govuk_as_sms_sender,
    sms_sender_is_govuk,
    volume_email,
    volume_sms,
    volume_letter,
    expected_readyness,
    agreement_signed,
    expected_tags,
):
    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(agreement_signed=agreement_signed)
    )

    for prop in {
        'has_team_members',
        'has_templates',
        'has_email_templates',
        'has_sms_templates',
        'has_email_reply_to_address',
        'shouldnt_use_govuk_as_sms_sender',
        'sms_sender_is_govuk',
    }:
        mocker.patch(
            'app.models.service.Service.{}'.format(prop),
            new_callable=PropertyMock
        ).return_value = locals()[prop]

    for channel, volume in (
        ('sms', volume_sms),
        ('email', volume_email),
        ('letter', volume_letter),
    ):
        mocker.patch(
            'app.models.service.Service.volume_{}'.format(channel),
            create=True,
            new_callable=PropertyMock,
            return_value=volume,
        )

    assert app.models.service.Service({
        'id': SERVICE_ONE_ID
    }).go_live_checklist_completed_as_yes_no == expected_readyness

    assert app.models.service.Service(
        {'id': SERVICE_ONE_ID}
    ).request_to_go_live_tags == expected_tags


@pytest.mark.parametrize('route', [
    'main.service_settings',
    'main.service_name_change',
    'main.service_name_change_confirm',
    'main.request_to_go_live',
    'main.submit_request_to_go_live',
    'main.archive_service'
])
def test_route_permissions(
        mocker,
        app_,
        client,
        api_user_active,
        service_one,
        single_reply_to_email_address,
        single_letter_contact_block,
        mock_get_organisation,
        mock_get_invites_for_service,
        single_sms_sender,
        route,
        mock_get_service_settings_page_common,
        mock_get_service_templates,
):
    validate_route_permission(
        mocker,
        app_,
        "GET",
        200,
        url_for(route, service_id=service_one['id']),
        ['manage_service'],
        api_user_active,
        service_one,
        session={'service_name_change': "New Service Name"}
    )


@pytest.mark.parametrize('route', [
    'main.service_settings',
    'main.service_name_change',
    'main.service_name_change_confirm',
    'main.request_to_go_live',
    'main.submit_request_to_go_live',
    'main.service_switch_live',
    'main.archive_service',
])
def test_route_invalid_permissions(
        mocker,
        app_,
        client,
        api_user_active,
        service_one,
        route,
        mock_get_service_templates,
        mock_get_invites_for_service,
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
    'main.request_to_go_live',
    'main.submit_request_to_go_live',
])
def test_route_for_platform_admin(
        mocker,
        app_,
        client,
        platform_admin_user,
        service_one,
        single_reply_to_email_address,
        single_letter_contact_block,
        mock_get_organisation,
        single_sms_sender,
        route,
        mock_get_service_settings_page_common,
        mock_get_service_templates,
        mock_get_invites_for_service,
):
    validate_route_permission(
        mocker,
        app_,
        "GET",
        200,
        url_for(route, service_id=service_one['id']),
        [],
        platform_admin_user,
        service_one,
        session={'service_name_change': "New Service Name"}
    )


def test_and_more_hint_appears_on_settings_with_more_than_just_a_single_sender(
        client_request,
        service_one,
        multiple_reply_to_email_addresses,
        multiple_letter_contact_blocks,
        mock_get_organisation,
        multiple_sms_senders,
        mock_get_service_settings_page_common,
):
    service_one['permissions'] = ['email', 'sms', 'letter']

    page = client_request.get(
        'main.service_settings',
        service_id=service_one['id']
    )

    def get_row(page, label):
        return normalize_spaces(
            find_element_by_tag_and_partial_text(page, tag='tr', string=label).text
        )

    assert get_row(page, 'Reply-to email addresses') == "Reply-to email addresses test@example.com …and 2 more Manage"
    assert get_row(page, 'Text message senders') == "Text message senders Example …and 2 more Manage"
    assert get_row(page, 'Sender addresses') == "Sender addresses 1 Example Street …and 2 more Manage"


@pytest.mark.parametrize('sender_list_page, index, expected_output', [
    ('main.service_email_reply_to', 0, 'test@example.com (default) Change'),
    ('main.service_letter_contact_details', 1, '1 Example Street (default) Change'),
    ('main.service_sms_senders', 0, 'GOVUK (default) Change')
])
def test_api_ids_dont_show_on_option_pages_with_a_single_sender(
    client_request,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    sender_list_page,
    index,
    expected_output,
):
    rows = client_request.get(
        sender_list_page,
        service_id=SERVICE_ONE_ID
    ).select(
        '.user-list-item'
    )

    assert normalize_spaces(rows[index].text) == expected_output
    assert len(rows) == index + 1


@pytest.mark.parametrize(
    (
        'sender_list_page,'
        'endpoint_to_mock,'
        'sample_data,'
        'expected_items,'
    ),
    [(
        'main.service_email_reply_to',
        'app.service_api_client.get_reply_to_email_addresses',
        create_multiple_email_reply_to_addresses(),
        [
            'test@example.com (default) Change 1234',
            'test2@example.com Change 5678',
            'test3@example.com Change 9457',
        ],
    ), (
        'main.service_letter_contact_details',
        'app.service_api_client.get_letter_contacts',
        create_multiple_letter_contact_blocks(),
        [
            'Blank Make default',
            '1 Example Street (default) Change 1234',
            '2 Example Street Change 5678',
            'foo<bar>baz Change 9457',
        ],
    ), (
        'main.service_sms_senders',
        'app.service_api_client.get_sms_senders',
        create_multiple_sms_senders(),
        [
            'Example (default and receives replies) Change 1234',
            'Example 2 Change 5678',
            'Example 3 Change 9457',
        ],
    ),
    ]
)
def test_default_option_shows_for_default_sender(
    client_request,
    mocker,
    sender_list_page,
    endpoint_to_mock,
    sample_data,
    expected_items,
):
    mocker.patch(endpoint_to_mock, return_value=sample_data)

    rows = client_request.get(
        sender_list_page,
        service_id=SERVICE_ONE_ID
    ).select(
        '.user-list-item'
    )

    assert [normalize_spaces(row.text) for row in rows] == expected_items


def test_remove_default_from_default_letter_contact_block(
    client_request,
    mocker,
    multiple_letter_contact_blocks,
    mock_update_letter_contact,
):
    letter_contact_details_page = url_for(
        'main.service_letter_contact_details',
        service_id=SERVICE_ONE_ID,
        _external=True,
    )

    link = client_request.get_url(letter_contact_details_page).select_one('.user-list-item a')
    assert link.text == 'Make default'
    assert link['href'] == url_for(
        '.service_make_blank_default_letter_contact',
        service_id=SERVICE_ONE_ID,
    )

    client_request.get_url(
        link['href'],
        _expected_status=302,
        _expected_redirect=letter_contact_details_page,
    )

    mock_update_letter_contact.assert_called_once_with(
        SERVICE_ONE_ID,
        letter_contact_id='1234',
        contact_block='1 Example Street',
        is_default=False,
    )


@pytest.mark.parametrize('sender_list_page, endpoint_to_mock, expected_output', [
    (
        'main.service_email_reply_to',
        'app.service_api_client.get_reply_to_email_addresses',
        'You have not added any reply-to email addresses yet'
    ),
    (
        'main.service_letter_contact_details',
        'app.service_api_client.get_letter_contacts',
        'Blank (default)'
    ),
    (
        'main.service_sms_senders',
        'app.service_api_client.get_sms_senders',
        'You have not added any text message senders yet'
    ),
])
def test_no_senders_message_shows(
    client_request,
    sender_list_page,
    endpoint_to_mock,
    expected_output,
    mocker
):
    mocker.patch(endpoint_to_mock, return_value=[])

    rows = client_request.get(
        sender_list_page,
        service_id=SERVICE_ONE_ID
    ).select(
        '.user-list-item'
    )

    assert normalize_spaces(rows[0].text) == expected_output
    assert len(rows) == 1


@pytest.mark.parametrize('reply_to_input, expected_error', [
    ('', 'Cannot be empty'),
    ('testtest', 'Enter a valid email address'),
])
def test_incorrect_reply_to_email_address_input(
    reply_to_input,
    expected_error,
    client_request,
    no_reply_to_email_addresses
):
    page = client_request.post(
        'main.service_add_email_reply_to',
        service_id=SERVICE_ONE_ID,
        _data={'email_address': reply_to_input},
        _expected_status=200
    )

    assert normalize_spaces(page.select_one('.error-message').text) == expected_error


@pytest.mark.parametrize('contact_block_input, expected_error', [
    ('', 'Cannot be empty'),
    ('1 \n 2 \n 3 \n 4 \n 5 \n 6 \n 7 \n 8 \n 9 \n 0 \n a', 'Contains 11 lines, maximum is 10')
])
def test_incorrect_letter_contact_block_input(
    contact_block_input,
    expected_error,
    client_request,
    no_letter_contact_blocks
):
    page = client_request.post(
        'main.service_add_letter_contact',
        service_id=SERVICE_ONE_ID,
        _data={'letter_contact_block': contact_block_input},
        _expected_status=200
    )

    assert normalize_spaces(page.select_one('.error-message').text) == expected_error


@pytest.mark.parametrize('sms_sender_input, expected_error', [
    ('elevenchars', None),
    ('11 chars', None),
    ('', 'Cannot be empty'),
    ('abcdefghijkhgkg', 'Enter 11 characters or fewer'),
    (r' ¯\_(ツ)_/¯ ', 'Use letters and numbers only'),
    ('blood.co.uk', None),
    ('00123', "Cannot start with 00")
])
def test_incorrect_sms_sender_input(
    sms_sender_input,
    expected_error,
    client_request,
    no_sms_senders,
    mock_add_sms_sender,
):
    page = client_request.post(
        'main.service_add_sms_sender',
        service_id=SERVICE_ONE_ID,
        _data={'sms_sender': sms_sender_input},
        _expected_status=(200 if expected_error else 302)
    )

    error_message = page.select_one('.error-message')
    count_of_api_calls = len(mock_add_sms_sender.call_args_list)

    if not expected_error:
        assert not error_message
        assert count_of_api_calls == 1
    else:
        assert normalize_spaces(error_message.text) == expected_error
        assert count_of_api_calls == 0


@pytest.mark.parametrize('reply_to_addresses, data, api_default_args', [
    ([], {}, True),
    (create_multiple_email_reply_to_addresses(), {}, False),
    (create_multiple_email_reply_to_addresses(), {"is_default": "y"}, True)
])
def test_add_reply_to_email_address_sends_test_notification(
    mocker, client_request, reply_to_addresses, data, api_default_args
):
    mocker.patch('app.service_api_client.get_reply_to_email_addresses', return_value=reply_to_addresses)
    data['email_address'] = "test@example.com"
    mock_verify = mocker.patch(
        'app.service_api_client.verify_reply_to_email_address', return_value={"data": {"id": "123"}}
    )
    client_request.post(
        'main.service_add_email_reply_to',
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_verify_reply_to_address',
            service_id=SERVICE_ONE_ID,
            notification_id="123",
            _external=True,
        ) + "?is_default={}".format(api_default_args)
    )
    mock_verify.assert_called_once_with(SERVICE_ONE_ID, "test@example.com")


@pytest.mark.parametrize("is_default,replace,expected_header", [(True, "&replace=123", "Change"), (False, "", "Add")])
@pytest.mark.parametrize("status,expected_failure,expected_success", [
    ("delivered", 0, 1),
    ("sending", 0, 0),
    ("permanent-failure", 1, 0),
])
@freeze_time("2018-06-01 11:11:00.061258")
def test_service_verify_reply_to_address(
    mocker,
    client_request,
    fake_uuid,
    get_non_default_reply_to_email_address,
    status,
    expected_failure,
    expected_success,
    is_default,
    replace,
    expected_header
):
    notification = {
        "id": fake_uuid,
        "status": status,
        "to": "email@example.gov.uk",
        "service_id": SERVICE_ONE_ID,
        "template_id": TEMPLATE_ONE_ID,
        "notification_type": "email",
        "created_at": '2018-06-01T11:10:52.499230+00:00'
    }
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)
    mock_add_reply_to_email_address = mocker.patch('app.service_api_client.add_reply_to_email_address')
    mock_update_reply_to_email_address = mocker.patch('app.service_api_client.update_reply_to_email_address')
    mocker.patch(
        'app.service_api_client.get_reply_to_email_addresses', return_value=[]
    )
    page = client_request.get(
        'main.service_verify_reply_to_address',
        service_id=SERVICE_ONE_ID,
        notification_id=notification["id"],
        _optional_args="?is_default={}{}".format(is_default, replace)
    )
    assert page.find('h1').text == '{} email reply-to address'.format(expected_header)
    if replace:
        assert "/email-reply-to/123/edit" in page.find('a', text="Back").attrs["href"]
    else:
        assert "/email-reply-to/add" in page.find('a', text="Back").attrs["href"]

    assert len(page.find_all('div', class_='banner-dangerous')) == expected_failure
    assert len(page.find_all('div', class_='banner-default-with-tick')) == expected_success

    if status == "delivered":
        if replace:
            mock_update_reply_to_email_address.assert_called_once_with(
                SERVICE_ONE_ID, "123", email_address=notification["to"], is_default=is_default
            )
            mock_add_reply_to_email_address.assert_not_called()
        else:
            mock_add_reply_to_email_address.assert_called_once_with(
                SERVICE_ONE_ID, email_address=notification["to"], is_default=is_default
            )
            mock_update_reply_to_email_address.assert_not_called()
    else:
        mock_add_reply_to_email_address.assert_not_called()
    if status == "permanent-failure":
        assert page.find('input', type='email').attrs["value"] == notification["to"]


@freeze_time("2018-06-01 11:11:00.061258")
def test_add_reply_to_email_address_fails_if_notification_not_delivered_in_45_sec(mocker, client_request, fake_uuid):
    notification = {
        "id": fake_uuid,
        "status": "sending",
        "to": "email@example.gov.uk",
        "service_id": SERVICE_ONE_ID,
        "template_id": TEMPLATE_ONE_ID,
        "notification_type": "email",
        "created_at": '2018-06-01T11:10:12.499230+00:00'
    }
    mocker.patch(
        'app.service_api_client.get_reply_to_email_addresses', return_value=[]
    )
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)
    mock_add_reply_to_email_address = mocker.patch('app.service_api_client.add_reply_to_email_address')
    page = client_request.get(
        'main.service_verify_reply_to_address',
        service_id=SERVICE_ONE_ID,
        notification_id=notification["id"],
        _optional_args="?is_default={}".format(False)
    )
    expected_banner = page.find_all('div', class_='banner-dangerous')[0]
    assert 'There’s a problem with your reply-to address' in expected_banner.text.strip()
    mock_add_reply_to_email_address.assert_not_called()


@pytest.mark.parametrize('letter_contact_blocks, data, api_default_args', [
    ([], {}, True),  # no existing letter contact blocks
    (create_multiple_letter_contact_blocks(), {}, False),
    (create_multiple_letter_contact_blocks(), {"is_default": "y"}, True)
])
def test_add_letter_contact(
    letter_contact_blocks,
    data,
    api_default_args,
    mocker,
    client_request,
    mock_add_letter_contact
):
    mocker.patch('app.service_api_client.get_letter_contacts', return_value=letter_contact_blocks)

    data['letter_contact_block'] = "1 Example Street"
    client_request.post(
        'main.service_add_letter_contact',
        service_id=SERVICE_ONE_ID,
        _data=data
    )

    mock_add_letter_contact.assert_called_once_with(
        SERVICE_ONE_ID,
        contact_block="1 Example Street",
        is_default=api_default_args
    )


def test_add_letter_contact_when_coming_from_template(
    no_letter_contact_blocks,
    client_request,
    mock_add_letter_contact,
    fake_uuid,
    mock_get_service_letter_template,
    mock_update_service_template_sender,
):
    page = client_request.get(
        'main.service_add_letter_contact',
        service_id=SERVICE_ONE_ID,
        from_template=fake_uuid,
    )

    assert page.select_one('.govuk-back-link')['href'] == url_for(
        'main.view_template',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    client_request.post(
        'main.service_add_letter_contact',
        service_id=SERVICE_ONE_ID,
        _data={
            'letter_contact_block': '1 Example Street',
        },
        from_template=fake_uuid,
        _expected_redirect=url_for(
            'main.view_template',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _external=True,
        ),
    )

    mock_add_letter_contact.assert_called_once_with(
        SERVICE_ONE_ID,
        contact_block="1 Example Street",
        is_default=True,
    )
    mock_update_service_template_sender.assert_called_once_with(
        SERVICE_ONE_ID,
        fake_uuid,
        '1234',
    )


@pytest.mark.parametrize('sms_senders, data, api_default_args', [
    ([], {}, True),
    (create_multiple_sms_senders(), {}, False),
    (create_multiple_sms_senders(), {"is_default": "y"}, True)
])
def test_add_sms_sender(
    sms_senders,
    data,
    api_default_args,
    mocker,
    client_request,
    mock_add_sms_sender
):
    mocker.patch('app.service_api_client.get_sms_senders', return_value=sms_senders)
    data['sms_sender'] = "Example"
    client_request.post(
        'main.service_add_sms_sender',
        service_id=SERVICE_ONE_ID,
        _data=data
    )

    mock_add_sms_sender.assert_called_once_with(
        SERVICE_ONE_ID,
        sms_sender="Example",
        is_default=api_default_args
    )


@pytest.mark.parametrize('reply_to_addresses, checkbox_present', [
    ([], False),
    (create_multiple_email_reply_to_addresses(), True),
])
def test_default_box_doesnt_show_on_first_email_sender(
    reply_to_addresses,
    mocker,
    checkbox_present,
    client_request
):
    mocker.patch('app.service_api_client.get_reply_to_email_addresses', return_value=reply_to_addresses)

    page = client_request.get(
        'main.service_add_email_reply_to',
        service_id=SERVICE_ONE_ID
    )

    assert bool(page.select_one('[name=is_default]')) == checkbox_present


@pytest.mark.parametrize('contact_blocks, checkbox_present', [
    ([], False),
    (create_multiple_letter_contact_blocks(), True)
])
def test_default_box_doesnt_show_on_first_letter_sender(
    contact_blocks,
    mocker,
    checkbox_present,
    client_request
):
    mocker.patch('app.service_api_client.get_letter_contacts', return_value=contact_blocks)

    page = client_request.get(
        'main.service_add_letter_contact',
        service_id=SERVICE_ONE_ID
    )

    assert bool(page.select_one('[name=is_default]')) == checkbox_present


@pytest.mark.parametrize('reply_to_address, data, api_default_args', [
    (create_reply_to_email_address(is_default=True), {"is_default": "y"}, True),
    (create_reply_to_email_address(is_default=True), {}, True),
    (create_reply_to_email_address(is_default=False), {}, False),
    (create_reply_to_email_address(is_default=False), {"is_default": "y"}, True)
])
def test_edit_reply_to_email_address_sends_verification_notification_if_address_is_changed(
    reply_to_address,
    data,
    api_default_args,
    mocker,
    fake_uuid,
    client_request,
):
    mock_verify = mocker.patch(
        'app.service_api_client.verify_reply_to_email_address', return_value={"data": {"id": "123"}}
    )
    mocker.patch('app.service_api_client.get_reply_to_email_address', return_value=reply_to_address)
    data['email_address'] = "test@example.gov.uk"
    client_request.post(
        'main.service_edit_email_reply_to',
        service_id=SERVICE_ONE_ID,
        reply_to_email_id=fake_uuid,
        _data=data
    )
    mock_verify.assert_called_once_with(SERVICE_ONE_ID, "test@example.gov.uk")


@pytest.mark.parametrize('reply_to_address, data, api_default_args', [
    (create_reply_to_email_address(), {"is_default": "y"}, True),
    (create_reply_to_email_address(), {}, True),
    (create_reply_to_email_address(is_default=False), {}, False),
    (create_reply_to_email_address(is_default=False), {"is_default": "y"}, True)
])
def test_edit_reply_to_email_address_goes_straight_to_update_if_address_not_changed(
    reply_to_address,
    data,
    api_default_args,
    mocker,
    fake_uuid,
    client_request,
    mock_update_reply_to_email_address
):
    mocker.patch('app.service_api_client.get_reply_to_email_address', return_value=reply_to_address)
    mock_verify = mocker.patch('app.service_api_client.verify_reply_to_email_address')
    data['email_address'] = "test@example.com"
    client_request.post(
        'main.service_edit_email_reply_to',
        service_id=SERVICE_ONE_ID,
        reply_to_email_id=fake_uuid,
        _data=data
    )

    mock_update_reply_to_email_address.assert_called_once_with(
        SERVICE_ONE_ID,
        reply_to_email_id=fake_uuid,
        email_address="test@example.com",
        is_default=api_default_args
    )
    mock_verify.assert_not_called()


@pytest.mark.parametrize('url', [
    'main.service_edit_email_reply_to',
    'main.service_add_email_reply_to',
])
def test_add_edit_reply_to_email_address_goes_straight_to_update_if_address_not_changed(
    mocker,
    fake_uuid,
    client_request,
    mock_update_reply_to_email_address,
    url
):
    reply_to_email_address = create_reply_to_email_address()
    mocker.patch('app.service_api_client.get_reply_to_email_addresses', return_value=[reply_to_email_address])
    mocker.patch('app.service_api_client.get_reply_to_email_address', return_value=reply_to_email_address)
    error_message = 'Your service already uses ‘reply_to@example.com’ as an email reply-to address.'
    mocker.patch(
        'app.service_api_client.verify_reply_to_email_address', side_effect=[HTTPError(
            response=Mock(
                status_code=409,
                json={
                    'result': 'error',
                    'message': error_message
                }
            ),
            message=error_message
        )]
    )
    data = {"is_default": "y", 'email_address': "reply_to@example.com"}
    page = client_request.post(
        url,
        service_id=SERVICE_ONE_ID,
        reply_to_email_id=fake_uuid,
        _data=data,
        _follow_redirects=True
    )

    assert page.find('h1').text == "Reply-to email addresses"
    assert error_message in page.find('div', class_='banner-dangerous').text

    mock_update_reply_to_email_address.assert_not_called()


@pytest.mark.parametrize('reply_to_address, expected_link_text, partial_href', [
    (
        create_reply_to_email_address(is_default=False),
        'Delete',
        partial(url_for, 'main.service_confirm_delete_email_reply_to', reply_to_email_id=sample_uuid()),
    ),
    (
        create_reply_to_email_address(is_default=True),
        None,
        None,
    ),
])
def test_shows_delete_link_for_email_reply_to_address(
    mocker,
    reply_to_address,
    expected_link_text,
    partial_href,
    fake_uuid,
    client_request,
):
    mocker.patch('app.service_api_client.get_reply_to_email_address', return_value=reply_to_address)

    page = client_request.get(
        'main.service_edit_email_reply_to',
        service_id=SERVICE_ONE_ID,
        reply_to_email_id=sample_uuid(),
    )

    assert page.select_one('.govuk-back-link').text.strip() == 'Back'
    assert page.select_one('.govuk-back-link')['href'] == url_for(
        '.service_email_reply_to',
        service_id=SERVICE_ONE_ID,
    )

    if expected_link_text:
        link = page.select_one('.page-footer a')
        assert normalize_spaces(link.text) == expected_link_text
        assert link['href'] == partial_href(service_id=SERVICE_ONE_ID)
    else:
        assert not page.select('.page-footer a')


def test_confirm_delete_reply_to_email_address(
    fake_uuid,
    client_request,
    get_non_default_reply_to_email_address
):

    page = client_request.get(
        'main.service_confirm_delete_email_reply_to',
        service_id=SERVICE_ONE_ID,
        reply_to_email_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        'Are you sure you want to delete this reply-to email address? '
        'Yes, delete'
    )
    assert 'action' not in page.select_one('.banner-dangerous form')
    assert page.select_one('.banner-dangerous form')['method'] == 'post'


def test_delete_reply_to_email_address(
    client_request,
    service_one,
    fake_uuid,
    get_non_default_reply_to_email_address,
    mocker,
):
    mock_delete = mocker.patch('app.service_api_client.delete_reply_to_email_address')
    client_request.post(
        '.service_delete_email_reply_to',
        service_id=SERVICE_ONE_ID,
        reply_to_email_id=fake_uuid,
        _expected_redirect=url_for(
            'main.service_email_reply_to',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )
    mock_delete.assert_called_once_with(service_id=SERVICE_ONE_ID, reply_to_email_id=fake_uuid)


@pytest.mark.parametrize('letter_contact_block, data, api_default_args', [
    (create_letter_contact_block(), {"is_default": "y"}, True),
    (create_letter_contact_block(), {}, True),
    (create_letter_contact_block(is_default=False), {}, False),
    (create_letter_contact_block(is_default=False), {"is_default": "y"}, True)
])
def test_edit_letter_contact_block(
    letter_contact_block,
    data,
    api_default_args,
    mocker,
    fake_uuid,
    client_request,
    mock_update_letter_contact
):
    mocker.patch('app.service_api_client.get_letter_contact', return_value=letter_contact_block)
    data['letter_contact_block'] = "1 Example Street"
    client_request.post(
        'main.service_edit_letter_contact',
        service_id=SERVICE_ONE_ID,
        letter_contact_id=fake_uuid,
        _data=data
    )

    mock_update_letter_contact.assert_called_once_with(
        SERVICE_ONE_ID,
        letter_contact_id=fake_uuid,
        contact_block="1 Example Street",
        is_default=api_default_args
    )


def test_confirm_delete_letter_contact_block(
    fake_uuid,
    client_request,
    get_default_letter_contact_block,
):

    page = client_request.get(
        'main.service_confirm_delete_letter_contact',
        service_id=SERVICE_ONE_ID,
        letter_contact_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        'Are you sure you want to delete this contact block? '
        'Yes, delete'
    )
    assert 'action' not in page.select_one('.banner-dangerous form')
    assert page.select_one('.banner-dangerous form')['method'] == 'post'


def test_delete_letter_contact_block(
    client_request,
    service_one,
    fake_uuid,
    get_default_letter_contact_block,
    mocker,
):
    mock_delete = mocker.patch('app.service_api_client.delete_letter_contact')
    client_request.post(
        '.service_delete_letter_contact',
        service_id=SERVICE_ONE_ID,
        letter_contact_id=fake_uuid,
        _expected_redirect=url_for(
            'main.service_letter_contact_details',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )
    mock_delete.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        letter_contact_id=fake_uuid,
    )


@pytest.mark.parametrize('sms_sender, data, api_default_args', [
    (create_sms_sender(), {"is_default": "y", "sms_sender": "test"}, True),
    (create_sms_sender(), {"sms_sender": "test"}, True),
    (create_sms_sender(is_default=False), {"sms_sender": "test"}, False),
    (create_sms_sender(is_default=False), {"is_default": "y", "sms_sender": "test"}, True)
])
def test_edit_sms_sender(
    sms_sender,
    data,
    api_default_args,
    mocker,
    fake_uuid,
    client_request,
    mock_update_sms_sender
):
    mocker.patch('app.service_api_client.get_sms_sender', return_value=sms_sender)

    client_request.post(
        'main.service_edit_sms_sender',
        service_id=SERVICE_ONE_ID,
        sms_sender_id=fake_uuid,
        _data=data
    )

    mock_update_sms_sender.assert_called_once_with(
        SERVICE_ONE_ID,
        sms_sender_id=fake_uuid,
        sms_sender="test",
        is_default=api_default_args
    )


@pytest.mark.parametrize('sender_page, endpoint_to_mock, sender_details, default_message, params, checkbox_present', [
    (
        'main.service_edit_email_reply_to',
        'app.service_api_client.get_reply_to_email_address',
        create_reply_to_email_address(is_default=True),
        'This is the default reply-to address for service one emails',
        'reply_to_email_id',
        False
    ),
    (
        'main.service_edit_email_reply_to',
        'app.service_api_client.get_reply_to_email_address',
        create_reply_to_email_address(is_default=False),
        'This is the default reply-to address for service one emails',
        'reply_to_email_id',
        True
    ),
    (
        'main.service_edit_letter_contact',
        'app.service_api_client.get_letter_contact',
        create_letter_contact_block(is_default=True),
        'This is currently your default address for service one.',
        'letter_contact_id',
        False
    ),
    (
        'main.service_edit_letter_contact',
        'app.service_api_client.get_letter_contact',
        create_letter_contact_block(is_default=False),
        'THIS TEXT WONT BE TESTED',
        'letter_contact_id',
        True
    ),
    (
        'main.service_edit_sms_sender',
        'app.service_api_client.get_sms_sender',
        create_sms_sender(is_default=True),
        'This is the default text message sender.',
        'sms_sender_id',
        False
    ),
    (
        'main.service_edit_sms_sender',
        'app.service_api_client.get_sms_sender',
        create_sms_sender(is_default=False),
        'This is the default text message sender.',
        'sms_sender_id',
        True
    )
])
def test_default_box_shows_on_non_default_sender_details_while_editing(
    fake_uuid,
    mocker,
    sender_page,
    endpoint_to_mock,
    sender_details,
    client_request,
    default_message,
    checkbox_present,
    params
):
    page_arguments = {
        'service_id': SERVICE_ONE_ID
    }
    page_arguments[params] = fake_uuid

    mocker.patch(endpoint_to_mock, return_value=sender_details)

    page = client_request.get(
        sender_page,
        **page_arguments
    )

    if checkbox_present:
        assert page.select_one('[name=is_default]')
    else:
        assert normalize_spaces(page.select_one('form p').text) == (
            default_message
        )


def test_sender_details_are_escaped(client_request, mocker, fake_uuid):
    letter_contact_block = create_letter_contact_block(contact_block='foo\n\n<br>\n\nbar')
    mocker.patch('app.service_api_client.get_letter_contacts', return_value=[letter_contact_block])

    page = client_request.get(
        'main.service_letter_contact_details',
        service_id=SERVICE_ONE_ID,
    )

    # get the second row (first is the default Blank sender)
    assert 'foo<br>bar' in normalize_spaces(page.select('.user-list-item')[1].text)


@pytest.mark.parametrize('sms_sender, expected_link_text, partial_href', [
    (
        create_sms_sender(is_default=False),
        'Delete',
        partial(url_for, 'main.service_confirm_delete_sms_sender', sms_sender_id=sample_uuid()),
    ),
    (
        create_sms_sender(is_default=True),
        None,
        None,
    ),
])
def test_shows_delete_link_for_sms_sender(
    mocker,
    sms_sender,
    expected_link_text,
    partial_href,
    fake_uuid,
    client_request,
):

    mocker.patch('app.service_api_client.get_sms_sender', return_value=sms_sender)

    page = client_request.get(
        'main.service_edit_sms_sender',
        service_id=SERVICE_ONE_ID,
        sms_sender_id=sample_uuid(),
    )

    link = page.select_one('.page-footer a')
    back_link = page.select_one('.govuk-back-link')

    assert back_link.text.strip() == 'Back'
    assert back_link['href'] == url_for(
        '.service_sms_senders',
        service_id=SERVICE_ONE_ID,
    )

    if expected_link_text:
        assert normalize_spaces(link.text) == expected_link_text
        assert link['href'] == partial_href(service_id=SERVICE_ONE_ID)
    else:
        assert not link


def test_confirm_delete_sms_sender(
    fake_uuid,
    client_request,
    get_non_default_sms_sender,
):

    page = client_request.get(
        'main.service_confirm_delete_sms_sender',
        service_id=SERVICE_ONE_ID,
        sms_sender_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        'Are you sure you want to delete this text message sender? '
        'Yes, delete'
    )
    assert 'action' not in page.select_one('.banner-dangerous form')
    assert page.select_one('.banner-dangerous form')['method'] == 'post'


@pytest.mark.parametrize('sms_sender, expected_link_text', [
    (create_sms_sender(is_default=False, inbound_number_id='1234'), None),
    (create_sms_sender(is_default=True), None),
    (create_sms_sender(is_default=False), 'Delete'),
])
def test_inbound_sms_sender_is_not_deleteable(
    client_request,
    service_one,
    fake_uuid,
    sms_sender,
    expected_link_text,
    mocker
):
    mocker.patch('app.service_api_client.get_sms_sender', return_value=sms_sender)

    page = client_request.get(
        '.service_edit_sms_sender',
        service_id=SERVICE_ONE_ID,
        sms_sender_id=fake_uuid,
    )

    back_link = page.select_one('.govuk-back-link')
    footer_link = page.select_one('.page-footer a')
    assert normalize_spaces(back_link.text) == 'Back'

    if expected_link_text:
        assert normalize_spaces(footer_link.text) == expected_link_text
    else:
        assert not footer_link


def test_delete_sms_sender(
    client_request,
    service_one,
    fake_uuid,
    get_non_default_sms_sender,
    mocker,
):
    mock_delete = mocker.patch('app.service_api_client.delete_sms_sender')
    client_request.post(
        '.service_delete_sms_sender',
        service_id=SERVICE_ONE_ID,
        sms_sender_id=fake_uuid,
        _expected_redirect=url_for(
            'main.service_sms_senders',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )
    mock_delete.assert_called_once_with(service_id=SERVICE_ONE_ID, sms_sender_id=fake_uuid)


@pytest.mark.parametrize('sms_sender, hide_textbox', [
    (create_sms_sender(is_default=False, inbound_number_id='1234'), True),
    (create_sms_sender(is_default=True), False),
])
def test_inbound_sms_sender_is_not_editable(
    client_request,
    service_one,
    fake_uuid,
    sms_sender,
    hide_textbox,
    mocker
):
    mocker.patch('app.service_api_client.get_sms_sender', return_value=sms_sender)

    page = client_request.get(
        '.service_edit_sms_sender',
        service_id=SERVICE_ONE_ID,
        sms_sender_id=fake_uuid,
    )

    assert bool(page.find('input', attrs={'name': "sms_sender"})) != hide_textbox
    if hide_textbox:
        assert normalize_spaces(
            page.select_one('form[method="post"] p').text
        ) == "GOVUK This phone number receives replies and cannot be changed"


def test_shows_research_mode_indicator(
    client_request,
    service_one,
    mocker,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    service_one['research_mode'] = True
    mocker.patch('app.service_api_client.update_service', return_value=service_one)

    page = client_request.get(
        'main.service_settings',
        service_id=SERVICE_ONE_ID,
    )

    element = page.find('span', {"id": "research-mode"})
    assert element.text == 'research mode'


def test_does_not_show_research_mode_indicator(
    client_request,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    page = client_request.get(
        'main.service_settings',
        service_id=SERVICE_ONE_ID,
    )

    element = page.find('span', {"id": "research-mode"})
    assert not element


def test_service_set_letter_branding_platform_admin_only(
    client_request,
):
    client_request.get(
        'main.service_set_letter_branding',
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


@pytest.mark.parametrize('letter_branding, expected_selected, expected_items', [
    # expected order: currently selected, then default, then rest alphabetically
    (None, '__NONE__', (
        ('__NONE__', 'None'),
        (str(UUID(int=2)), 'Animal and Plant Health Agency'),
        (str(UUID(int=0)), 'HM Government'),
        (str(UUID(int=1)), 'Land Registry'),
    )),
    (str(UUID(int=1)), str(UUID(int=1)), (
        (str(UUID(int=1)), 'Land Registry'),
        ('__NONE__', 'None'),
        (str(UUID(int=2)), 'Animal and Plant Health Agency'),
        (str(UUID(int=0)), 'HM Government'),
    )),
    (str(UUID(int=2)), str(UUID(int=2)), (
        (str(UUID(int=2)), 'Animal and Plant Health Agency'),
        ('__NONE__', 'None'),
        (str(UUID(int=0)), 'HM Government'),
        (str(UUID(int=1)), 'Land Registry'),
    )),
])
@pytest.mark.parametrize('endpoint, extra_args', (
    (
        'main.service_set_letter_branding',
        {'service_id': SERVICE_ONE_ID},
    ),
    (
        'main.edit_organisation_letter_branding',
        {'org_id': ORGANISATION_ID},
    ),
))
def test_service_set_letter_branding_prepopulates(
    mocker,
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation,
    mock_get_all_letter_branding,
    letter_branding,
    expected_selected,
    expected_items,
    endpoint,
    extra_args,
):
    service_one['letter_branding'] = letter_branding
    mocker.patch(
        'app.organisations_client.get_organisation',
        side_effect=lambda org_id: organisation_json(
            org_id,
            'Org 1',
            letter_branding_id=letter_branding,
        )
    )

    client_request.login(platform_admin_user)
    page = client_request.get(
        endpoint,
        **extra_args,
    )

    assert len(page.select('input[checked]')) == 1
    assert page.select('input[checked]')[0]['value'] == expected_selected

    for element in {'label[for^=branding_style]', 'input[type=radio]'}:
        assert len(page.select(element)) == len(expected_items)

    for index, expected_item in enumerate(expected_items):
        expected_value, expected_label = expected_item
        assert normalize_spaces(page.select('label[for^=branding_style]')[index].text) == expected_label
        assert page.select('input[type=radio]')[index]['value'] == expected_value


@pytest.mark.parametrize('selected_letter_branding, expected_post_data', [
    (str(UUID(int=1)), str(UUID(int=1))),
    ('__NONE__', None),
])
@pytest.mark.parametrize('endpoint, extra_args, expected_redirect', (
    (
        'main.service_set_letter_branding',
        {'service_id': SERVICE_ONE_ID},
        'main.service_preview_letter_branding',
    ),
    (
        'main.edit_organisation_letter_branding',
        {'org_id': ORGANISATION_ID},
        'main.organisation_preview_letter_branding',
    ),
))
def test_service_set_letter_branding_redirects_to_preview_page_when_form_submitted(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mock_get_all_letter_branding,
    selected_letter_branding,
    expected_post_data,
    endpoint,
    extra_args,
    expected_redirect,
):
    client_request.login(platform_admin_user)
    client_request.post(
        endpoint,
        _data={'branding_style': selected_letter_branding},
        _expected_status=302,
        _expected_redirect=url_for(
            expected_redirect,
            branding_style=expected_post_data,
            _external=True,
            **extra_args
        ),
        **extra_args
    )


@pytest.mark.parametrize('endpoint, extra_args', (
    (
        'main.service_preview_letter_branding',
        {'service_id': SERVICE_ONE_ID},
    ),
    (
        'main.organisation_preview_letter_branding',
        {'org_id': ORGANISATION_ID},
    ),
))
def test_service_preview_letter_branding_shows_preview_letter(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mock_get_all_letter_branding,
    endpoint,
    extra_args,
):
    client_request.login(platform_admin_user)

    page = client_request.get(
        endpoint,
        branding_style='hm-government',
        **extra_args
    )

    assert page.find('iframe')['src'] == url_for('main.letter_template', branding_style='hm-government')


@pytest.mark.parametrize('selected_letter_branding, expected_post_data', [
    (str(UUID(int=1)), str(UUID(int=1))),
    ('__NONE__', None),
])
@pytest.mark.parametrize('endpoint, extra_args, expected_redirect', (
    (
        'main.service_preview_letter_branding',
        {'service_id': SERVICE_ONE_ID},
        'main.service_settings',
    ),
    (
        'main.organisation_preview_letter_branding',
        {'org_id': ORGANISATION_ID},
        'main.organisation_settings',
    ),
))
def test_service_preview_letter_branding_saves(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mock_get_organisation_services,
    mock_update_service,
    mock_update_organisation,
    mock_get_all_letter_branding,
    selected_letter_branding,
    expected_post_data,
    endpoint,
    extra_args,
    expected_redirect,
):
    client_request.login(platform_admin_user)
    client_request.post(
        endpoint,
        _data={'branding_style': selected_letter_branding},
        _expected_status=302,
        _expected_redirect=url_for(
            expected_redirect,
            _external=True,
            **extra_args
        ),
        **extra_args
    )

    if endpoint == 'main.service_preview_letter_branding':
        mock_update_service.assert_called_once_with(
            SERVICE_ONE_ID,
            letter_branding=expected_post_data,
        )
        assert mock_update_organisation.called is False

    elif endpoint == 'main.organisation_preview_letter_branding':
        mock_update_organisation.assert_called_once_with(
            ORGANISATION_ID,
            letter_branding_id=expected_post_data,
            cached_service_ids=[
                '12345',
                '67890',
                '596364a0-858e-42c8-9062-a8fe822260eb',
            ],
        )
        assert mock_update_service.called is False

    else:
        raise Exception


@pytest.mark.parametrize('current_branding, expected_values, expected_labels', [
    (None, [
        '__NONE__', '1', '2', '3', '4', '5',
    ], [
        'GOV.UK', 'org 1', 'org 2', 'org 3', 'org 4', 'org 5'
    ]),
    ('5', [
        '5', '__NONE__', '1', '2', '3', '4',
    ], [
        'org 5', 'GOV.UK', 'org 1', 'org 2', 'org 3', 'org 4',
    ]),
])
@pytest.mark.parametrize('endpoint, extra_args', (
    (
        'main.service_set_email_branding',
        {'service_id': SERVICE_ONE_ID},
    ),
    (
        'main.edit_organisation_email_branding',
        {'org_id': ORGANISATION_ID},
    ),
))
def test_should_show_branding_styles(
    mocker,
    client_request,
    platform_admin_user,
    service_one,
    mock_get_all_email_branding,
    current_branding,
    expected_values,
    expected_labels,
    endpoint,
    extra_args,
):
    service_one['email_branding'] = current_branding
    mocker.patch(
        'app.organisations_client.get_organisation',
        side_effect=lambda org_id: organisation_json(
            org_id,
            'Org 1',
            email_branding_id=current_branding,
        )
    )

    client_request.login(platform_admin_user)
    page = client_request.get(endpoint, **extra_args)

    branding_style_choices = page.find_all('input', attrs={"name": "branding_style"})

    radio_labels = [
        page.find('label', attrs={"for": branding_style_choices[idx]['id']}).get_text().strip()
        for idx, element in enumerate(branding_style_choices)]

    assert len(branding_style_choices) == 6

    for index, expected_value in enumerate(expected_values):
        assert branding_style_choices[index]['value'] == expected_value

    # radios should be in alphabetical order, based on their labels
    assert radio_labels == expected_labels

    assert 'checked' in branding_style_choices[0].attrs
    assert 'checked' not in branding_style_choices[1].attrs
    assert 'checked' not in branding_style_choices[2].attrs
    assert 'checked' not in branding_style_choices[3].attrs
    assert 'checked' not in branding_style_choices[4].attrs
    assert 'checked' not in branding_style_choices[5].attrs

    app.email_branding_client.get_all_email_branding.assert_called_once_with()
    app.service_api_client.get_service.assert_called_once_with(service_one['id'])


@pytest.mark.parametrize('endpoint, extra_args, expected_redirect', (
    (
        'main.service_set_email_branding',
        {'service_id': SERVICE_ONE_ID},
        'main.service_preview_email_branding',
    ),
    (
        'main.edit_organisation_email_branding',
        {'org_id': ORGANISATION_ID},
        'main.organisation_preview_email_branding',
    ),
))
def test_should_send_branding_and_organisations_to_preview(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation,
    mock_get_all_email_branding,
    mock_update_service,
    endpoint,
    extra_args,
    expected_redirect,
):
    client_request.login(platform_admin_user)
    client_request.post(
        endpoint,
        data={
            'branding_type': 'org',
            'branding_style': '1'
        },
        _expected_status=302,
        _expected_location=url_for(
            expected_redirect,
            branding_style='1',
            _external=True,
            **extra_args
        ),
        **extra_args
    )

    mock_get_all_email_branding.assert_called_once_with()


@pytest.mark.parametrize('endpoint, extra_args', (
    (
        'main.service_preview_email_branding',
        {'service_id': SERVICE_ONE_ID},
    ),
    (
        'main.organisation_preview_email_branding',
        {'org_id': ORGANISATION_ID},
    ),
))
def test_should_preview_email_branding(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    endpoint,
    extra_args,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        endpoint,
        branding_type='org',
        branding_style='1',
        **extra_args
    )

    iframe = page.find('iframe', attrs={"class": "branding-preview"})
    iframeURLComponents = urlparse(iframe['src'])
    iframeQString = parse_qs(iframeURLComponents.query)

    assert page.find('input', attrs={"id": "branding_style"})['value'] == '1'
    assert iframeURLComponents.path == '/_email'
    assert iframeQString['branding_style'] == ['1']


@pytest.mark.parametrize('posted_value, submitted_value', (
    ('1', '1'),
    ('__NONE__', None),
    pytest.param('None', None, marks=pytest.mark.xfail(raises=AssertionError)),
))
@pytest.mark.parametrize('endpoint, extra_args, expected_redirect', (
    (
        'main.service_preview_email_branding',
        {'service_id': SERVICE_ONE_ID},
        'main.service_settings',
    ),
    (
        'main.organisation_preview_email_branding',
        {'org_id': ORGANISATION_ID},
        'main.organisation_settings',
    ),
))
def test_should_set_branding_and_organisations(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation,
    mock_get_organisation_services,
    mock_update_service,
    mock_update_organisation,
    posted_value,
    submitted_value,
    endpoint,
    extra_args,
    expected_redirect,
):
    client_request.login(platform_admin_user)
    client_request.post(
        endpoint,
        _data={
            'branding_style': posted_value
        },
        _expected_status=302,
        _expected_redirect=url_for(
            expected_redirect,
            _external=True,
            **extra_args
        ),
        **extra_args
    )

    if endpoint == 'main.service_preview_email_branding':
        mock_update_service.assert_called_once_with(
            SERVICE_ONE_ID,
            email_branding=submitted_value,
        )
        assert mock_update_organisation.called is False
    elif endpoint == 'main.organisation_preview_email_branding':
        mock_update_organisation.assert_called_once_with(
            ORGANISATION_ID,
            email_branding_id=submitted_value,
            cached_service_ids=[
                '12345',
                '67890',
                '596364a0-858e-42c8-9062-a8fe822260eb',
            ],
        )
        assert mock_update_service.called is False
    else:
        raise Exception


@pytest.mark.parametrize('method', ['get', 'post'])
@pytest.mark.parametrize('endpoint', [
    'main.set_free_sms_allowance',
])
def test_organisation_type_pages_are_platform_admin_only(
    client_request,
    method,
    endpoint,
):
    getattr(client_request, method)(
        endpoint,
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
        _test_page_title=False,
    )


def test_should_show_page_to_set_sms_allowance(
    platform_admin_client,
    mock_get_free_sms_fragment_limit
):
    response = platform_admin_client.get(url_for(
        'main.set_free_sms_allowance',
        service_id=SERVICE_ONE_ID
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(page.select_one('label').text) == 'Numbers of text message fragments per year'
    mock_get_free_sms_fragment_limit.assert_called_once_with(SERVICE_ONE_ID)


@freeze_time("2017-04-01 11:09:00.061258")
@pytest.mark.parametrize('given_allowance, expected_api_argument', [
    ('1', 1),
    ('250000', 250000),
    pytest.param('foo', 'foo', marks=pytest.mark.xfail),
])
def test_should_set_sms_allowance(
    platform_admin_client,
    given_allowance,
    expected_api_argument,
    mock_get_free_sms_fragment_limit,
    mock_create_or_update_free_sms_fragment_limit,
):

    response = platform_admin_client.post(
        url_for(
            'main.set_free_sms_allowance',
            service_id=SERVICE_ONE_ID,
        ),
        data={
            'free_sms_allowance': given_allowance,
        },
    )
    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=SERVICE_ONE_ID, _external=True)

    mock_create_or_update_free_sms_fragment_limit.assert_called_with(
        SERVICE_ONE_ID,
        expected_api_argument
    )


def test_old_set_letters_page_redirects(
    client_request,
):
    client_request.get(
        'main.service_set_letters',
        service_id=SERVICE_ONE_ID,
        _expected_status=301,
        _expected_redirect=url_for(
            'main.service_set_channel',
            service_id=SERVICE_ONE_ID,
            channel='letter',
            _external=True,
        )
    )


def test_unknown_channel_404s(
    client_request,
):
    client_request.get(
        'main.service_set_channel',
        service_id=SERVICE_ONE_ID,
        channel='message-in-a-bottle',
        _expected_status=404,
    )


@pytest.mark.parametrize((
    'channel,'
    'expected_first_para,'
    'expected_legend,'
    'initial_permissions,'
    'expected_initial_value,'
    'posted_value,'
    'expected_updated_permissions'
), [
    (
        'letter',
        'It costs between 35p and £1.16 to send a letter using Notify.',
        'Send letters',
        ['email', 'sms'],
        'False',
        'True',
        ['email', 'sms', 'letter'],
    ),
    (
        'letter',
        'It costs between 35p and £1.16 to send a letter using Notify.',
        'Send letters',
        ['email', 'sms', 'letter'],
        'True',
        'False',
        ['email', 'sms'],
    ),
    (
        'sms',
        'You have a free allowance of 250,000 text messages each financial year.',
        'Send text messages',
        [],
        'False',
        'True',
        ['sms'],
    ),
    (
        'email',
        'It’s free to send emails through GOV.UK Notify.',
        'Send emails',
        [],
        'False',
        'True',
        ['email'],
    ),
    (
        'email',
        'It’s free to send emails through GOV.UK Notify.',
        'Send emails',
        ['email', 'sms', 'letter'],
        'True',
        'True',
        ['email', 'sms', 'letter'],
    ),
])
def test_switch_service_channels_on_and_off(
    client_request,
    service_one,
    mocker,
    mock_get_free_sms_fragment_limit,
    channel,
    expected_first_para,
    expected_legend,
    initial_permissions,
    expected_initial_value,
    posted_value,
    expected_updated_permissions,
):
    mocked_fn = mocker.patch('app.service_api_client.update_service', return_value=service_one)
    service_one['permissions'] = initial_permissions

    page = client_request.get(
        'main.service_set_channel',
        service_id=service_one['id'],
        channel=channel,
    )

    assert normalize_spaces(page.select_one('main p').text) == expected_first_para
    assert normalize_spaces(page.select_one('legend').text) == expected_legend

    assert page.select_one('input[checked]')['value'] == expected_initial_value
    assert len(page.select('input[checked]')) == 1

    client_request.post(
        'main.service_set_channel',
        service_id=service_one['id'],
        channel=channel,
        _data={'enabled': posted_value},
        _expected_redirect=url_for(
            'main.service_settings',
            service_id=service_one['id'],
            _external=True
        )
    )
    assert set(mocked_fn.call_args[1]['permissions']) == set(expected_updated_permissions)
    assert mocked_fn.call_args[0][0] == service_one['id']


@pytest.mark.parametrize('channel', (
    'email', 'sms', 'letter',
))
def test_broadcast_service_cant_post_to_set_other_channels_endpoint(
    client_request,
    service_one,
    channel,
):
    service_one['permissions'] = ['broadcast']

    client_request.get(
        'main.service_set_channel',
        service_id=SERVICE_ONE_ID,
        channel=channel,
        _expected_status=403,
    )

    client_request.post(
        'main.service_set_channel',
        service_id=SERVICE_ONE_ID,
        channel=channel,
        _data={'enabled': 'True'},
        _expected_status=403,
    )


@pytest.mark.parametrize('permissions, expected_checked', [
    (['international_sms'], 'on'),
    ([''], 'off'),
])
def test_show_international_sms_as_radio_button(
    client_request,
    service_one,
    mocker,
    permissions,
    expected_checked,
):
    service_one['permissions'] = permissions

    checked_radios = client_request.get(
        'main.service_set_international_sms',
        service_id=service_one['id'],
    ).select(
        '.multiple-choice input[checked]'
    )

    assert len(checked_radios) == 1
    assert checked_radios[0]['value'] == expected_checked


@pytest.mark.parametrize('post_value, international_sms_permission_expected_in_api_call', [
    ('on', True),
    ('off', False),
])
def test_switch_service_enable_international_sms(
    client_request,
    service_one,
    mocker,
    post_value,
    international_sms_permission_expected_in_api_call,
):
    mocked_fn = mocker.patch('app.service_api_client.update_service', return_value=service_one)
    client_request.post(
        'main.service_set_international_sms',
        service_id=service_one['id'],
        _data={
            'enabled': post_value
        },
        _expected_redirect=url_for('main.service_settings', service_id=service_one['id'], _external=True)
    )

    if international_sms_permission_expected_in_api_call:
        assert 'international_sms' in mocked_fn.call_args[1]['permissions']
    else:
        assert 'international_sms' not in mocked_fn.call_args[1]['permissions']

    assert mocked_fn.call_args[0][0] == service_one['id']


@pytest.mark.parametrize('user', (
    create_platform_admin_user(),
    create_active_user_with_permissions(),
    pytest.param(create_active_user_no_settings_permission(), marks=pytest.mark.xfail),
))
def test_archive_service_after_confirm(
    client_request,
    mocker,
    mock_get_organisations,
    mock_get_service_and_organisation_counts,
    mock_get_organisations_and_services_for_user,
    mock_get_users_by_service,
    user,
):
    mocked_fn = mocker.patch('app.service_api_client.post')
    redis_delete_mock = mocker.patch('app.notify_client.service_api_client.redis_client.delete')
    client_request.login(user)
    page = client_request.post(
        'main.archive_service',
        service_id=SERVICE_ONE_ID,
        _follow_redirects=True,
    )

    mocked_fn.assert_called_once_with('/service/{}/archive'.format(SERVICE_ONE_ID), data=None)
    assert normalize_spaces(page.select_one('h1').text) == 'Choose service'
    assert normalize_spaces(page.select_one('.banner-default-with-tick').text) == (
        '‘service one’ was deleted'
    )
    # The one user which is part of this service has the sample_uuid as it's user ID
    assert call(f"user-{sample_uuid()}") in redis_delete_mock.call_args_list


@pytest.mark.parametrize('user', (
    create_platform_admin_user(),
    create_active_user_with_permissions(),
    pytest.param(create_active_user_no_settings_permission(), marks=pytest.mark.xfail),
))
def test_archive_service_prompts_user(
    client_request,
    mocker,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common,
    user,
):
    mocked_fn = mocker.patch('app.service_api_client.post')
    client_request.login(user)

    settings_page = client_request.get(
        'main.archive_service',
        service_id=SERVICE_ONE_ID
    )
    delete_link = settings_page.select('.page-footer-delete-link a')[0]
    assert normalize_spaces(delete_link.text) == 'Delete this service'
    assert delete_link['href'] == url_for(
        'main.archive_service',
        service_id=SERVICE_ONE_ID,
    )

    delete_page = client_request.get(
        'main.archive_service',
        service_id=SERVICE_ONE_ID,
    )
    assert normalize_spaces(delete_page.select_one('.banner-dangerous').text) == (
        'Are you sure you want to delete ‘service one’? '
        'There’s no way to undo this. '
        'Yes, delete'
    )
    assert mocked_fn.called is False


def test_cant_archive_inactive_service(
    platform_admin_client,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common
):
    service_one['active'] = False

    response = platform_admin_client.get(url_for('main.service_settings', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Delete service' not in {a.text for a in page.find_all('a', class_='button')}


def test_suspend_service_after_confirm(
    platform_admin_client,
    service_one,
    mocker,
    mock_get_inbound_number_for_service,
):
    mocked_fn = mocker.patch('app.service_api_client.post', return_value=service_one)

    response = platform_admin_client.post(url_for('main.suspend_service', service_id=service_one['id']))

    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    assert mocked_fn.call_args == call('/service/{}/suspend'.format(service_one['id']), data=None)


def test_suspend_service_prompts_user(
    platform_admin_client,
    service_one,
    mocker,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    mocked_fn = mocker.patch('app.service_api_client.post')

    response = platform_admin_client.get(url_for('main.suspend_service', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'This will suspend the service and revoke all api keys. Are you sure you want to suspend this service?' in \
           page.find('div', class_='banner-dangerous').text
    assert mocked_fn.called is False


def test_cant_suspend_inactive_service(
    platform_admin_client,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    service_one['active'] = False

    response = platform_admin_client.get(url_for('main.service_settings', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Suspend service' not in {a.text for a in page.find_all('a', class_='button')}


def test_resume_service_after_confirm(
    platform_admin_client,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    mocker,
    mock_get_inbound_number_for_service,
):
    service_one['active'] = False
    mocked_fn = mocker.patch('app.service_api_client.post', return_value=service_one)

    response = platform_admin_client.post(url_for('main.resume_service', service_id=service_one['id']))

    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    assert mocked_fn.call_args == call('/service/{}/resume'.format(service_one['id']), data=None)


def test_resume_service_prompts_user(
    platform_admin_client,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    mocker,
    mock_get_service_settings_page_common,
):
    service_one['active'] = False
    mocked_fn = mocker.patch('app.service_api_client.post')

    response = platform_admin_client.get(url_for('main.resume_service', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'This will resume the service. New api key are required for this service to use the API.' in \
           page.find('div', class_='banner-dangerous').text
    assert mocked_fn.called is False


def test_cant_resume_active_service(
    platform_admin_client,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common
):
    response = platform_admin_client.get(url_for('main.service_settings', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Resume service' not in {a.text for a in page.find_all('a', class_='button')}


@pytest.mark.parametrize('contact_details_type, contact_details_value', [
    ('url', 'http://example.com/'),
    ('email_address', 'me@example.com'),
    ('phone_number', '0207 123 4567'),
])
def test_send_files_by_email_contact_details_prefills_the_form_with_the_existing_contact_details(
    client_request,
    service_one,
    contact_details_type,
    contact_details_value,
):
    service_one['contact_link'] = contact_details_value

    page = client_request.get(
        'main.send_files_by_email_contact_details', service_id=SERVICE_ONE_ID
    )
    assert page.find('input', attrs={'name': 'contact_details_type', 'value': contact_details_type}).has_attr('checked')
    assert page.find('input', {'id': contact_details_type}).get('value') == contact_details_value


@pytest.mark.parametrize('contact_details_type, old_value, new_value', [
    ('url', 'http://example.com/', 'http://new-link.com/'),
    ('email_address', 'old@example.com', 'new@example.com'),
    ('phone_number', '0207 12345', '0207 56789'),
])
def test_send_files_by_email_contact_details_updates_contact_details_and_redirects_to_settings_page(
    client_request,
    service_one,
    mock_update_service,
    mock_get_service_settings_page_common,
    mock_get_organisation,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    contact_details_type,
    old_value,
    new_value,
):
    service_one['contact_link'] = old_value

    page = client_request.post(
        'main.send_files_by_email_contact_details', service_id=SERVICE_ONE_ID,
        _data={
            'contact_details_type': contact_details_type,
            contact_details_type: new_value,
        },
        _follow_redirects=True
    )

    assert page.h1.text == 'Settings'
    mock_update_service.assert_called_once_with(SERVICE_ONE_ID, contact_link=new_value)


def test_send_files_by_email_contact_details_uses_the_selected_field_when_multiple_textboxes_contain_data(
    client_request,
    service_one,
    mock_update_service,
    mock_get_service_settings_page_common,
    mock_get_organisation,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
):
    service_one['contact_link'] = 'http://www.old-url.com'

    page = client_request.post(
        'main.send_files_by_email_contact_details', service_id=SERVICE_ONE_ID,
        _data={
            'contact_details_type': 'url',
            'url': 'http://www.new-url.com',
            'email_address': 'me@example.com',
            'phone_number': '0207 123 4567'
        },
        _follow_redirects=True
    )

    assert page.h1.text == 'Settings'
    mock_update_service.assert_called_once_with(SERVICE_ONE_ID, contact_link='http://www.new-url.com')


@pytest.mark.parametrize(
    'contact_link, subheader, button_selected',
    [
        ('contact.me@gov.uk', 'Change contact details for the file download page', True),
        (None, 'Add contact details to the file download page', False),
    ]
)
def test_send_files_by_email_contact_details_page(
    client_request, service_one, active_user_with_permissions, contact_link, subheader, button_selected
):
    service_one["contact_link"] = contact_link
    page = client_request.get(
        'main.send_files_by_email_contact_details', service_id=SERVICE_ONE_ID
    )
    assert normalize_spaces(page.find_all('h2')[1].text) == subheader
    if button_selected:
        assert 'checked' in page.find('input', {'name': 'contact_details_type', 'value': 'email_address'}).attrs
    else:
        assert 'checked' not in page.find('input', {'name': 'contact_details_type', 'value': 'email_address'}).attrs


def test_send_files_by_email_contact_details_displays_error_message_when_no_radio_button_selected(
    client_request,
    service_one
):
    page = client_request.post(
        'main.send_files_by_email_contact_details', service_id=SERVICE_ONE_ID,
        _data={
            'contact_details_type': None,
            'url': '',
            'email_address': '',
            'phone_number': '',
        },
        _follow_redirects=True
    )
    assert normalize_spaces(page.find('span', class_='error-message').text) == 'Select an option'
    assert normalize_spaces(page.h1.text) == "Send files by email"


@pytest.mark.parametrize('contact_details_type, invalid_value, error', [
    ('url', 'invalid.com/', 'Must be a valid URL'),
    ('email_address', 'me@co', 'Enter a valid email address'),
    ('phone_number', 'abcde', 'Must be a valid phone number'),
])
def test_send_files_by_email_contact_details_does_not_update_invalid_contact_details(
    mocker,
    client_request,
    service_one,
    contact_details_type,
    invalid_value,
    error,
):
    service_one['contact_link'] = 'http://example.com/'
    service_one['permissions'].append('upload_document')

    page = client_request.post(
        'main.send_files_by_email_contact_details', service_id=SERVICE_ONE_ID,
        _data={
            'contact_details_type': contact_details_type,
            contact_details_type: invalid_value,
        },
        _follow_redirects=True
    )

    assert normalize_spaces(page.find('span', class_='error-message').text) == error
    assert normalize_spaces(page.h1.text) == "Send files by email"


def test_contact_link_is_not_displayed_without_the_upload_document_permission(
    client_request,
    service_one,
    mock_get_service_settings_page_common,
    mock_get_organisation,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
):
    page = client_request.get(
        'main.service_settings',
        service_id=SERVICE_ONE_ID,
    )
    assert 'Contact details' not in page.text


@pytest.mark.parametrize('endpoint, permissions, expected_p', [
    (
        'main.service_set_inbound_sms',
        ['sms'],
        (
            'Contact us if you want to be able to receive text messages from your users.'
        )
    ),
    (
        'main.service_set_inbound_sms',
        ['sms', 'inbound_sms'],
        (
            'Your service can receive text messages sent to 0781239871.'
        )
    ),
    (
        'main.service_set_auth_type',
        [],
        (
            'Text message code'
        )
    ),
    (
        'main.service_set_auth_type',
        ['email_auth'],
        (
            'Email link or text message code'
        )
    ),
])
def test_invitation_pages(
    client_request,
    service_one,
    mock_get_inbound_number_for_service,
    single_sms_sender,
    endpoint,
    permissions,
    expected_p,
):
    service_one['permissions'] = permissions
    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
    )

    assert normalize_spaces(page.select('main p')[0].text) == expected_p


def test_service_settings_when_inbound_number_is_not_set(
    client_request,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    mocker,
    mock_get_all_letter_branding,
    mock_get_free_sms_fragment_limit,
    mock_get_service_data_retention,
):
    mocker.patch('app.inbound_number_client.get_inbound_sms_number_for_service',
                 return_value={'data': {}})
    client_request.get(
        'main.service_settings',
        service_id=SERVICE_ONE_ID,
    )


def test_set_inbound_sms_when_inbound_number_is_not_set(
    client_request,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    single_sms_sender,
    mocker,
    mock_get_all_letter_branding,
):
    mocker.patch('app.inbound_number_client.get_inbound_sms_number_for_service',
                 return_value={'data': {}})
    client_request.get(
        'main.service_set_inbound_sms',
        service_id=SERVICE_ONE_ID,
    )


@pytest.mark.parametrize('user, expected_paragraphs', [
    (create_active_user_with_permissions(), [
        'Your service can receive text messages sent to 07700900123.',
        'You can still send text messages from a sender name if you '
        'need to, but users will not be able to reply to those messages.',
        'Contact us if you want to switch this feature off.',
        'You can set up callbacks for received text messages on the API integration page.',
    ]),
    (create_active_user_no_api_key_permission(), [
        'Your service can receive text messages sent to 07700900123.',
        'You can still send text messages from a sender name if you '
        'need to, but users will not be able to reply to those messages.',
        'Contact us if you want to switch this feature off.',
    ]),
])
def test_set_inbound_sms_when_inbound_number_is_set(
    client_request,
    service_one,
    mocker,
    user,
    expected_paragraphs,
):
    service_one['permissions'] = ['inbound_sms']
    mocker.patch('app.inbound_number_client.get_inbound_sms_number_for_service', return_value={
        'data': {'number': '07700900123'}
    })
    client_request.login(user)
    page = client_request.get(
        'main.service_set_inbound_sms',
        service_id=SERVICE_ONE_ID,
    )
    paragraphs = page.select('main p')

    assert len(paragraphs) == len(expected_paragraphs)

    for index, p in enumerate(expected_paragraphs):
        assert normalize_spaces(paragraphs[index].text) == p


def test_show_sms_prefixing_setting_page(
    client_request,
    mock_update_service,
):
    page = client_request.get(
        'main.service_set_sms_prefix', service_id=SERVICE_ONE_ID
    )
    assert normalize_spaces(page.select_one('legend').text) == (
        'Start all text messages with ‘service one:’'
    )
    radios = page.select('input[type=radio]')
    assert len(radios) == 2
    assert radios[0]['value'] == 'on'
    assert radios[0]['checked'] == ''
    assert radios[1]['value'] == 'off'
    with pytest.raises(KeyError):
        assert radios[1]['checked']


@pytest.mark.parametrize('post_value, expected_api_argument', [
    ('on', True),
    ('off', False),
])
def test_updates_sms_prefixing(
    client_request,
    mock_update_service,
    post_value,
    expected_api_argument,
):
    client_request.post(
        'main.service_set_sms_prefix', service_id=SERVICE_ONE_ID,
        _data={'enabled': post_value},
        _expected_redirect=url_for(
            'main.service_settings', service_id=SERVICE_ONE_ID,
            _external=True
        )
    )
    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        prefix_sms=expected_api_argument,
    )


def test_select_organisation(
    platform_admin_client,
    service_one,
    mock_get_organisation,
    mock_get_organisations
):
    response = platform_admin_client.get(
        url_for('.link_service_to_organisation', service_id=service_one['id']),
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert len(page.select('.multiple-choice')) == 3
    for i in range(0, 3):
        assert normalize_spaces(
            page.select('.multiple-choice label')[i].text
        ) == 'Org {}'.format(i + 1)


def test_select_organisation_shows_message_if_no_orgs(
    platform_admin_client,
    service_one,
    mock_get_organisation,
    mocker
):
    mocker.patch('app.organisations_client.get_organisations', return_value=[])

    response = platform_admin_client.get(
        url_for('.link_service_to_organisation', service_id=service_one['id']),
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(page.select_one('main p').text) == "No organisations"
    assert not page.select_one('main button')


def test_update_service_organisation(
    platform_admin_client,
    service_one,
    mock_get_organisation,
    mock_get_organisations,
    mock_update_service_organisation,
):
    response = platform_admin_client.post(
        url_for('.link_service_to_organisation', service_id=service_one['id']),
        data={'organisations': '7aa5d4e9-4385-4488-a489-07812ba13384'},
    )

    assert response.status_code == 302
    mock_update_service_organisation.assert_called_once_with(
        service_one['id'],
        '7aa5d4e9-4385-4488-a489-07812ba13384'
    )


def test_update_service_organisation_does_not_update_if_same_value(
    platform_admin_client,
    service_one,
    mock_get_organisation,
    mock_get_organisations,
    mock_update_service_organisation,
):
    response = platform_admin_client.post(
        url_for('.link_service_to_organisation', service_id=service_one['id']),
        data={'organisations': '7aa5d4e9-4385-4488-a489-07812ba13383'},
    )

    assert response.status_code == 302
    mock_update_service_organisation.called is False


@pytest.mark.parametrize('branding_type', ['email', 'letter'])
@pytest.mark.parametrize('organisation_type, expected_options', (
    ('central', None),
    ('local', None),
    ('nhs_central', [
        ('nhs', 'NHS'),
        ('something_else', 'Something else'),
    ]),
    ('nhs_local', [
        ('nhs', 'NHS'),
        ('something_else', 'Something else'),
    ]),
    ('nhs_gp', [
        ('nhs', 'NHS'),
        ('something_else', 'Something else'),
    ]),
    ('emergency_service', None),
    ('other', None),
))
def test_show_branding_request_page_when_no_branding_is_set(
    mocker,
    service_one,
    client_request,
    mock_get_email_branding,
    mock_get_letter_branding_by_id,
    organisation_type,
    expected_options,
    branding_type
):
    service_one['{}_branding'.format(branding_type)] = None
    service_one['organisation_type'] = organisation_type

    page = client_request.get(
        '.branding_request', service_id=SERVICE_ONE_ID, branding_type=branding_type
    )

    mock_get_email_branding.assert_not_called()
    mock_get_letter_branding_by_id.assert_not_called()

    if expected_options:
        assert [
            (
                radio['value'],
                page.select_one('label[for={}]'.format(radio['id'])).text.strip()
            )
            for radio in page.select('input[type=radio]')
        ] == expected_options
        assert page.select_one(
            '.conditional-radios-panel#panel-something-else textarea'
        )['name'] == (
            'something_else'
        )
    else:
        assert page.select_one(
            'textarea'
        )['name'] == (
            'something_else'
        )
        assert not page.select('.conditional-radios-panel')


@pytest.mark.parametrize('branding_type', ['email', 'letter'])
@pytest.mark.parametrize('organisation_type, expected_options', (
    ('local', [
        ('organisation', 'Test Organisation'),
        ('something_else', 'Something else'),
    ]),
    ('nhs_central', [
        ('nhs', 'NHS'),
        ('something_else', 'Something else'),
    ]),
    ('nhs_local', [
        ('nhs', 'NHS'),
        ('something_else', 'Something else'),
    ]),
    ('nhs_gp', [
        ('nhs', 'NHS'),
        ('something_else', 'Something else'),
    ]),
    ('emergency_service', [
        ('organisation', 'Test Organisation'),
        ('something_else', 'Something else'),
    ]),
    ('other', [
        ('organisation', 'Test Organisation'),
        ('something_else', 'Something else'),
    ]),
))
def test_show_branding_request_page_when_no_branding_is_set_but_organisation_exists(
    mocker,
    service_one,
    client_request,
    mock_get_email_branding,
    mock_get_letter_branding_by_id,
    mock_get_service_organisation,
    organisation_type,
    expected_options,
    branding_type
):
    service_one['{}_branding'.format(branding_type)] = None
    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(organisation_type=organisation_type),
    )

    page = client_request.get(
        '.branding_request', service_id=SERVICE_ONE_ID, branding_type=branding_type
    )

    mock_get_email_branding.assert_not_called()
    mock_get_letter_branding_by_id.assert_not_called()

    assert [
        (
            radio['value'],
            page.select_one('label[for={}]'.format(radio['id'])).text.strip()
        )
        for radio in page.select('input[type=radio]')
    ] == expected_options


@pytest.mark.parametrize('organisation_type, expected_options, branding_type', (
    ('central', [
        ('govuk_and_org', 'GOV.UK and Test Organisation'),
        ('organisation', 'Test Organisation'),
        ('something_else', 'Something else'),
    ], 'email'),
    ('central', [
        ('organisation', 'Test Organisation'),
        ('something_else', 'Something else'),
    ], 'letter'),
))
def test_show_branding_request_page_when_no_branding_is_set_but_organisation_exists_central_org(
    mocker,
    service_one,
    client_request,
    mock_get_email_branding,
    mock_get_letter_branding_by_id,
    mock_get_service_organisation,
    organisation_type,
    expected_options,
    branding_type
):
    service_one['{}_branding'.format(branding_type)] = None
    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(organisation_type=organisation_type),
    )

    page = client_request.get(
        '.branding_request', service_id=SERVICE_ONE_ID, branding_type=branding_type
    )

    mock_get_email_branding.assert_not_called()
    mock_get_letter_branding_by_id.assert_not_called()

    assert [
        (
            radio['value'],
            page.select_one('label[for={}]'.format(radio['id'])).text.strip()
        )
        for radio in page.select('input[type=radio]')
    ] == expected_options


def test_show_email_branding_request_page_when_email_branding_is_set(
    mocker,
    service_one,
    client_request,
    mock_get_email_branding,
    mock_get_service_organisation,
    active_user_with_permissions,
):
    service_one['email_branding'] = sample_uuid()
    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(),
    )

    page = client_request.get(
        '.branding_request', service_id=SERVICE_ONE_ID, branding_type="email"
    )
    assert [
        (
            radio['value'],
            page.select_one('label[for={}]'.format(radio['id'])).text.strip()
        )
        for radio in page.select('input[type=radio]')
    ] == [
        ('govuk', 'GOV.UK'),
        ('govuk_and_org', 'GOV.UK and Test Organisation'),
        ('organisation', 'Test Organisation'),
        ('something_else', 'Something else'),
    ]


def test_show_letter_branding_request_page_when_letter_branding_is_set(
    mocker,
    service_one,
    client_request,
    mock_get_letter_branding_by_id,
    mock_get_service_organisation,
    active_user_with_permissions,
):
    service_one['letter_branding'] = sample_uuid()
    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(),
    )

    page = client_request.get(
        '.branding_request', service_id=SERVICE_ONE_ID, branding_type="letter"
    )
    assert [
        (
            radio['value'],
            page.select_one('label[for={}]'.format(radio['id'])).text.strip()
        )
        for radio in page.select('input[type=radio]')
    ] == [
        ('organisation', 'Test Organisation'),
        ('something_else', 'Something else'),
    ]


@pytest.mark.parametrize('branding_type', ['email', 'letter'])
@pytest.mark.parametrize('from_template,back_link_url', [
    (None, '/services/{}/service-settings'.format(SERVICE_ONE_ID),),
    (TEMPLATE_ONE_ID, '/services/{}/templates/{}'.format(SERVICE_ONE_ID, TEMPLATE_ONE_ID),)
])
def test_back_link_on_branding_request_page(
    mocker,
    service_one,
    client_request,
    mock_get_email_branding,
    mock_get_letter_branding_by_id,
    active_user_with_permissions,
    from_template,
    back_link_url,
    branding_type,
):
    if from_template:
        page = client_request.get(
            '.branding_request', service_id=SERVICE_ONE_ID, branding_type=branding_type, from_template=from_template
        )
    else:
        page = client_request.get(
            '.branding_request', service_id=SERVICE_ONE_ID, branding_type=branding_type
        )

    back_link = page.select('a[class=govuk-back-link]')
    assert back_link[0].attrs['href'] == back_link_url


@pytest.mark.parametrize('branding_type', ['email', 'letter'])
def test_show_branding_request_page_when_branding_is_same_as_org(
    mocker,
    service_one,
    client_request,
    mock_get_email_branding,
    mock_get_letter_branding_by_id,
    mock_get_service_organisation,
    active_user_with_permissions,
    branding_type
):
    service_one['{}_branding'.format(branding_type)] = sample_uuid()
    if branding_type == 'email':
        mocker.patch(
            'app.organisations_client.get_organisation',
            return_value=organisation_json(email_branding_id=service_one['email_branding']),
        )
    else:
        mocker.patch(
            'app.organisations_client.get_organisation',
            return_value=organisation_json(letter_branding_id=service_one['letter_branding']),
        )

    page = client_request.get(
        '.branding_request', service_id=SERVICE_ONE_ID, branding_type=branding_type
    )

    # Central government organisations who have their own default
    # branding will do so because they’re exempt from GOV.UK.
    # We also don’t show their organisation’s branding because they
    # have it already. So ‘Something else’ is the only option.
    assert not page.select('input[type=radio]')
    assert page.select_one('textarea')['name'] == 'something_else'


@pytest.mark.parametrize('data, requested_branding', (
    (
        {
            'options': 'govuk',
        },
        'GOV.UK',
    ),
    (
        {
            'options': 'govuk',
            'something_else': 'ignored',
        },
        'GOV.UK',
    ),
    (
        {
            'options': 'something_else',
            'something_else': 'Homer Simpson'
        },
        'Something else\n\nHomer Simpson'
    ),
    pytest.param(
        {
            'options': 'something_else',
        },
        '[Missing details]',
        marks=pytest.mark.xfail(raises=AssertionError),
    ),
    pytest.param(
        {'options': 'foo'},
        'Nope',
        marks=pytest.mark.xfail(raises=AssertionError),
    ),
))
@pytest.mark.parametrize('org_name, expected_organisation', (
    (None, 'Can’t tell (domain is user.gov.uk)'),
    ('Test Organisation', 'Test Organisation'),
))
def test_submit_email_branding_request(
    client_request,
    service_one,
    mocker,
    data,
    requested_branding,
    mock_get_service_settings_page_common,
    mock_get_email_branding,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    org_name,
    expected_organisation,
):
    service_one['email_branding'] = sample_uuid()
    mocker.patch(
        'app.models.service.Service.organisation_id',
        new_callable=PropertyMock,
        return_value=ORGANISATION_ID if org_name else None,
    )
    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(name=org_name),
    )

    zendesk = mocker.patch(
        'app.main.views.service_settings.zendesk_client.create_ticket',
        autospec=True,
    )

    page = client_request.post(
        '.branding_request', service_id=SERVICE_ONE_ID, branding_type="email",
        _data=data,
        _follow_redirects=True,
    )

    zendesk.assert_called_once_with(
        message='\n'.join([
            'Organisation: {}',
            'Service: service one',
            'http://localhost/services/596364a0-858e-42c8-9062-a8fe822260eb',
            '',
            '---',
            'Current branding: Organisation name',
            'Branding requested: {}\n',
        ]).format(expected_organisation, requested_branding),
        subject='Email branding request - service one',
        ticket_type='question',
        user_email='test@user.gov.uk',
        user_name='Test User',
        tags=['notify_action', 'notify_branding'],
    )
    assert normalize_spaces(page.select_one('.banner-default').text) == (
        'Thanks for your branding request. We’ll get back to you '
        'within one working day.'
    )


@pytest.mark.parametrize('data, requested_branding', (
    (
        {
            'options': 'something_else',
            'something_else': 'Homer Simpson'
        },
        'Something else\n\nHomer Simpson'
    ),
    pytest.param(
        {
            'options': 'something_else',
        },
        '[Missing details]',
        marks=pytest.mark.xfail(raises=AssertionError),
    ),
    pytest.param(
        {'options': 'foo'},
        'Nope',
        marks=pytest.mark.xfail(raises=AssertionError),
    ),
))
@pytest.mark.parametrize('org_name, expected_organisation', (
    (None, 'Can’t tell (domain is user.gov.uk)'),
    ('Test Organisation', 'Test Organisation'),
))
def test_submit_letter_branding_request(
    client_request,
    service_one,
    mocker,
    data,
    requested_branding,
    mock_get_service_settings_page_common,
    mock_get_letter_branding_by_id,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    org_name,
    expected_organisation,
):
    service_one['letter_branding'] = sample_uuid()

    mocker.patch(
        'app.models.service.Service.organisation_id',
        new_callable=PropertyMock,
        return_value=ORGANISATION_ID if org_name else None,
    )
    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(name=org_name),
    )

    zendesk = mocker.patch(
        'app.main.views.service_settings.zendesk_client.create_ticket',
        autospec=True,
    )

    page = client_request.post(
        '.branding_request', service_id=SERVICE_ONE_ID, branding_type="letter",
        _data=data,
        _follow_redirects=True,
    )

    zendesk.assert_called_once_with(
        message='\n'.join([
            'Organisation: {}',
            'Service: service one',
            'http://localhost/services/596364a0-858e-42c8-9062-a8fe822260eb',
            '',
            '---',
            'Current branding: HM Government',
            'Branding requested: {}\n',
        ]).format(expected_organisation, requested_branding),
        subject='Letter branding request - service one',
        ticket_type='question',
        user_email='test@user.gov.uk',
        user_name='Test User',
        tags=['notify_action', 'notify_branding'],
    )
    assert normalize_spaces(page.select_one('.banner-default').text) == (
        'Thanks for your branding request. We’ll get back to you '
        'within one working day.'
    )


@pytest.mark.parametrize('branding_type', ['email', 'letter'])
@pytest.mark.parametrize('from_template', [
    None,
    TEMPLATE_ONE_ID
])
def test_submit_letter_branding_request_redirects_if_from_template_is_set(
    client_request,
    service_one,
    mocker,
    mock_get_service_settings_page_common,
    mock_get_letter_branding_by_id,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    from_template,
    branding_type,

):
    mocker.patch('app.main.views.service_settings.zendesk_client.create_ticket', autospec=True)
    data = {'options': 'something_else', 'something_else': 'Homer Simpson'}

    if from_template:
        client_request.post(
            '.branding_request', service_id=SERVICE_ONE_ID, branding_type="letter", from_template=from_template,
            _data=data,
            _expected_redirect=url_for(
                'main.view_template', service_id=SERVICE_ONE_ID, template_id=from_template, _external=True
            )
        )
    else:
        client_request.post(
            '.branding_request', service_id=SERVICE_ONE_ID, branding_type="letter",
            _data=data,
            _expected_redirect=url_for('main.service_settings', service_id=SERVICE_ONE_ID, _external=True)
        )


@pytest.mark.parametrize('branding_type,current_branding', [
    ('email', 'GOV.UK'), ('letter', 'no')
])
def test_submit_branding_when_something_else_is_only_option(
    client_request,
    service_one,
    mocker,
    mock_get_service_settings_page_common,
    mock_get_email_branding,
    mock_get_letter_branding_by_id,
    branding_type,
    current_branding,
):
    zendesk = mocker.patch(
        'app.main.views.service_settings.zendesk_client.create_ticket',
        autospec=True,
    )

    client_request.post(
        '.branding_request',
        service_id=SERVICE_ONE_ID, branding_type=branding_type,
        _data={
            'something_else': 'Homer Simpson',
        },
    )

    assert (
        'Current branding: {}\n'
        'Branding requested: Something else\n'
        '\n'
        'Homer Simpson'.format(current_branding)
    ) in zendesk.call_args_list[0][1]['message']


def test_service_settings_links_to_branding_request_page_for_letters(
    mocker,
    service_one,
    client_request,
    active_user_with_permissions,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_service_settings_page_common,
    mock_get_organisation,
):
    service_one["restricted"] is False
    service_one['permissions'].append('letter')
    page = client_request.get(
        '.service_settings', service_id=SERVICE_ONE_ID
    )
    assert len(page.find_all('a', attrs={'href': '/services/{}/branding-request/letter'.format(SERVICE_ONE_ID)})) == 1


def test_show_service_data_retention(
        platform_admin_client,
        service_one,
        mock_get_service_data_retention,

):

    mock_get_service_data_retention.return_value[0]['days_of_retention'] = 5

    response = platform_admin_client.get(url_for('main.data_retention', service_id=service_one['id']))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    rows = page.select('tbody tr')
    assert len(rows) == 1
    assert normalize_spaces(rows[0].text) == 'Email 5 Change'


def test_view_add_service_data_retention(
        platform_admin_client,
        service_one,

):
    response = platform_admin_client.get(url_for('main.add_data_retention', service_id=service_one['id']))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert normalize_spaces(page.select_one('input')['value']) == "email"
    assert page.find('input', attrs={'name': 'days_of_retention'})


def test_add_service_data_retention(
        platform_admin_client,
        service_one,
        mock_create_service_data_retention
):
    response = platform_admin_client.post(url_for(
        'main.add_data_retention',
        service_id=service_one['id']),
        data={'notification_type': "email", 'days_of_retention': 5}
    )
    assert response.status_code == 302
    settings_url = url_for(
        'main.data_retention', service_id=service_one['id'], _external=True)
    assert settings_url == response.location
    assert mock_create_service_data_retention.called


def test_update_service_data_retention(
        platform_admin_client,
        service_one,
        fake_uuid,
        mock_get_service_data_retention,
        mock_update_service_data_retention,
):
    response = platform_admin_client.post(
        url_for(
            'main.edit_data_retention',
            service_id=service_one['id'],
            data_retention_id=str(fake_uuid)),
        data={'days_of_retention': 5}
    )
    assert response.status_code == 302
    settings_url = url_for(
        'main.data_retention', service_id=service_one['id'], _external=True)
    assert settings_url == response.location
    assert mock_update_service_data_retention.called


def test_update_service_data_retention_return_validation_error_for_negative_days_of_retention(
        platform_admin_client,
        service_one,
        fake_uuid,
        mock_get_service_data_retention,
        mock_update_service_data_retention,
):
    response = platform_admin_client.post(
        url_for(
            'main.edit_data_retention',
            service_id=service_one['id'],
            data_retention_id=fake_uuid
        ),
        data={'days_of_retention': -5}
    )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    error_message = page.find('span', class_='error-message').text.strip()
    assert error_message == 'Must be between 3 and 90'
    assert mock_get_service_data_retention.called
    assert not mock_update_service_data_retention.called


def test_update_service_data_retention_populates_form(
        platform_admin_client,
        service_one,
        fake_uuid,
        mock_get_service_data_retention,
):

    mock_get_service_data_retention.return_value[0]['days_of_retention'] = 5
    response = platform_admin_client.get(url_for(
        'main.edit_data_retention',
        service_id=service_one['id'],
        data_retention_id=fake_uuid
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('input', attrs={'name': 'days_of_retention'})['value'] == '5'
