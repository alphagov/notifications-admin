from functools import partial
from unittest.mock import ANY, PropertyMock, call
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from freezegun import freeze_time
from notifications_utils.clients.zendesk.zendesk_client import ZendeskClient

import app
from app.utils import email_safe
from tests import (
    organisation_json,
    sample_uuid,
    service_json,
    validate_route_permission,
)
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
    active_user_no_api_key_permission,
    active_user_no_settings_permission,
    active_user_with_permissions,
    get_default_letter_contact_block,
    get_default_reply_to_email_address,
    get_default_sms_sender,
    get_inbound_number_sms_sender,
    get_non_default_letter_contact_block,
    get_non_default_reply_to_email_address,
    get_non_default_sms_sender,
    multiple_letter_contact_blocks,
    multiple_reply_to_email_addresses,
    multiple_sms_senders,
    no_letter_contact_blocks,
    no_reply_to_email_addresses,
    no_sms_senders,
    normalize_spaces,
    platform_admin_user,
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
    (active_user_with_permissions, [

        'Label Value Action',
        'Service name service one Change',
        'Sign-in method Text message code Change',

        'Label Value Action',
        'Send emails On Change',
        'Email reply-to addresses Not set Change',
        'Email branding GOV.UK Change',

        'Label Value Action',
        'Send text messages On Change',
        'Text message sender GOVUK Change',
        'Text messages start with service name On Change',
        'International text messages Off Change',
        'Receive text messages Off Change',

        'Label Value Action',
        'Send letters Off Change',

    ]),
    (platform_admin_user, [

        'Label Value Action',
        'Service name service one Change',
        'Sign-in method Text message code Change',

        'Label Value Action',
        'Send emails On Change',
        'Email reply-to addresses Not set Change',
        'Email branding GOV.UK Change',

        'Label Value Action',
        'Send text messages On Change',
        'Text message sender GOVUK Change',
        'Text messages start with service name On Change',
        'International text messages Off Change',
        'Receive text messages Off Change',

        'Label Value Action',
        'Send letters Off Change',

        'Label Value Action',
        'Live Off Change',
        'Count in list of live services Yes Change',
        'Organisation Org 1 Change',
        'Organisation type Central Change',
        'Free text message allowance 250,000 Change',
        'Email branding GOV.UK Change',
        'Letter branding Not set Change',
        'Data retention email Change',
        'Receive inbound SMS Off Change',
        'User auth type editing Off Change',
        'Uploading documents Off Change',
        'Folder permissions Off Change',

    ]),
])
def test_should_show_overview(
        client,
        mocker,
        service_one,
        fake_uuid,
        no_reply_to_email_addresses,
        no_letter_contact_blocks,
        mock_get_service_organisation,
        single_sms_sender,
        user,
        expected_rows,
        mock_get_service_settings_page_common,
):

    service_one['permissions'] = ['sms', 'email']

    client.login(user(fake_uuid), mocker, service_one)
    response = client.get(url_for(
        'main.service_settings', service_id=service_one['id']
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('h1').text == 'Settings'
    rows = page.select('tr')
    assert len(rows) == len(expected_rows)
    for index, row in enumerate(expected_rows):
        assert row == " ".join(rows[index].text.split())
    app.service_api_client.get_service.assert_called_with(service_one['id'])


@pytest.mark.parametrize('permissions, expected_rows', [
    (['email', 'sms', 'inbound_sms', 'international_sms'], [

        'Service name service one Change',
        'Sign-in method Text message code Change',

        'Label Value Action',
        'Send emails On Change',
        'Email reply-to addresses test@example.com Manage',
        'Email branding GOV.UK Change',

        'Label Value Action',
        'Send text messages On Change',
        'Text message sender GOVUK Change',
        'Text messages start with service name On Change',
        'International text messages On Change',
        'Receive text messages On Change',

        'Label Value Action',
        'Send letters Off Change',

    ]),
    (['email', 'sms', 'email_auth'], [

        'Service name service one Change',
        'Sign-in method Email link or text message code Change',

        'Label Value Action',
        'Send emails On Change',
        'Email reply-to addresses test@example.com Manage',
        'Email branding GOV.UK Change',

        'Label Value Action',
        'Send text messages On Change',
        'Text message sender GOVUK Change',
        'Text messages start with service name On Change',
        'International text messages Off Change',
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
])
def test_should_show_overview_for_service_with_more_things_set(
        client,
        active_user_with_permissions,
        mocker,
        service_one,
        single_reply_to_email_address,
        single_letter_contact_block,
        single_sms_sender,
        mock_get_service_organisation,
        mock_get_email_branding,
        mock_get_service_settings_page_common,
        permissions,
        expected_rows
):
    client.login(active_user_with_permissions, mocker, service_one)
    service_one['permissions'] = permissions
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
        mock_get_service_organisation,
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
    mock_get_service_organisation,
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
    mock_get_service_organisation,
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
        'at the start of every text message, eg ‘service one: This is an example message’ '
        'as your email sender name'
    )
    app.service_api_client.get_service.assert_called_with(SERVICE_ONE_ID)


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


@pytest.mark.parametrize('user, expected_text, expected_link', [
    (
        active_user_with_permissions,
        'To remove these restrictions request to go live.',
        True,
    ),
    (
        active_user_no_settings_permission,
        'Your service manager can ask to have these restrictions removed.',
        False,
    ),
])
def test_show_restricted_service(
    client_request,
    fake_uuid,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_service_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common,
    user,
    expected_text,
    expected_link,
):
    client_request.login(user(fake_uuid))
    page = client_request.get(
        'main.service_settings',
        service_id=SERVICE_ONE_ID,
    )

    assert page.find('h1').text == 'Settings'
    assert page.find_all('h2')[0].text == 'Your service is in trial mode'

    request_to_live = page.select_one('main p')
    request_to_live_link = request_to_live.select_one('a')

    assert normalize_spaces(request_to_live.text) == expected_text

    if expected_link:
        assert request_to_live_link.text.strip() == 'request to go live'
        assert request_to_live_link['href'] == url_for('main.request_to_go_live', service_id=SERVICE_ONE_ID)
    else:
        assert not request_to_live_link


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
        restricted=False
    )


def test_show_live_service(
    client_request,
    mock_get_live_service,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_service_organisation,
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


@pytest.mark.parametrize('count_of_users_with_manage_service, expected_user_checklist_item', [
    (1, 'Add a team member who can manage settings, team and usage Not completed'),
    (2, 'Add a team member who can manage settings, team and usage Completed'),
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
    (None, 1, [], 'Add an email reply-to address Not completed'),
    (None, 1, [{}], 'Add an email reply-to address Completed'),
    (1, 1, [], 'Add an email reply-to address Not completed'),
    (1, 1, [{}], 'Add an email reply-to address Completed'),
    (1, 0, [], 'Add an email reply-to address Not completed'),
    (1, 0, [{}], 'Add an email reply-to address Completed'),
])
def test_should_check_for_sending_things_right(
    client_request,
    mocker,
    single_sms_sender,
    count_of_users_with_manage_service,
    expected_user_checklist_item,
    count_of_templates,
    expected_templates_checklist_item,
    volume_email,
    count_of_email_templates,
    reply_to_email_addresses,
    expected_reply_to_checklist_item,
):

    def _templates_by_type(template_type):
        return {
            'email': list(range(0, count_of_email_templates)),
            'sms': [],
        }.get(template_type)

    mock_count_users = mocker.patch(
        'app.main.views.service_settings.user_api_client.get_count_of_users_with_permission',
        return_value=count_of_users_with_manage_service
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

    assert page.select_one('form')['method'] == 'post'
    assert 'action' not in page.select_one('form')

    mock_count_users.assert_called_once_with(SERVICE_ONE_ID, 'manage_service')
    assert mock_templates.call_args_list == [
        call(),
    ]

    if count_of_email_templates:
        mock_get_reply_to_email_addresses.assert_called_once_with(SERVICE_ONE_ID)


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
        None,
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
        'local',
        0,
        [],
        'Change your text message sender name Not completed',
    ),
    (
        None,
        'local',
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
        'nhs',
        1,
        [{'is_default': True, 'sms_sender': 'KUVOG'}],
        'Change your text message sender name Completed',
    ),
])
def test_should_check_for_sms_sender_on_go_live(
    client_request,
    service_one,
    mocker,
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
        'app.main.views.service_settings.user_api_client.get_count_of_users_with_permission',
        return_value=99,
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

    assert mock_templates.call_args_list == [
        call(),
    ]

    mock_get_sms_senders.assert_called_once_with(SERVICE_ONE_ID)


@pytest.mark.parametrize('email_address, expected_item', (
    pytest.param(
        'test@unknown.gov.uk',
        '',
        marks=pytest.mark.xfail(raises=IndexError)
    ),
    (
        'test@education.gov.uk',
        'Sign our data sharing and financial agreement Completed',
    ),
    (
        'test@aylesbury.gov.uk',
        'Sign our data sharing and financial agreement Not completed',
    ),
))
def test_should_check_for_mou_on_request_to_go_live(
    client_request,
    service_one,
    mocker,
    email_address,
    expected_item,
):
    mocker.patch(
        'app.main.views.service_settings.user_api_client.get_count_of_users_with_permission',
        return_value=0,
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

    user = active_user_with_permissions(uuid4())
    user.email_address = email_address
    client_request.login(user)

    page = client_request.get(
        'main.request_to_go_live', service_id=SERVICE_ONE_ID
    )
    assert page.h1.text == 'Before you request to go live'

    checklist_items = page.select('.task-list .task-list-item')
    assert normalize_spaces(checklist_items[3].text) == expected_item


def test_non_gov_user_is_told_they_cant_go_live(
    client_request,
    api_nongov_user_active,
    mocker,
):
    mocker.patch(
        'app.main.views.service_settings.user_api_client.get_count_of_users_with_permission',
        return_value=0,
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
    assert page.select('form') == []
    assert page.select('button') == []


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
        'This field is required.'
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
        ['notify_request_to_go_live_incomplete_volumes']
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
@freeze_time("2012-12-21")
def test_should_redirect_after_request_to_go_live(
    client_request,
    mocker,
    active_user_with_permissions,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_service_organisation,
    mock_get_organisations_and_services_for_user,
    single_sms_sender,
    mock_get_service_settings_page_common,
    mock_get_service_templates,
    mock_get_users_by_service,
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
        user_name=active_user_with_permissions.name,
        user_email=active_user_with_permissions.email_address,
        tags=[
            'notify_request_to_go_live',
            'notify_request_to_go_live_incomplete',
        ] + extra_tags + [
            'notify_request_to_go_live_incomplete_checklist',
            'notify_request_to_go_live_incomplete_mou',
            'notify_request_to_go_live_incomplete_team_member',
        ],
    )
    assert mock_post.call_args[1]['message'] == (
        'Service: service one\n'
        'http://localhost/services/{service_id}\n'
        '\n'
        '---\n'
        'Organisation type: Central\n'
        'Agreement signed: Can’t tell (domain is user.gov.uk)\n'
        'Checklist completed: No\n'
        '{formatted_displayed_volumes}'
        'Consent to research: Yes\n'
        'Other live services: No\n'
        '\n'
        '---\n'
        '{service_id}, None, service one, Test User, test@user.gov.uk, -, 21/12/2012, '
        '{displayed_volumes}'
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
                'notify_request_to_go_live',
                'notify_request_to_go_live_complete',
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
                'notify_request_to_go_live',
                'notify_request_to_go_live_incomplete',
                'notify_request_to_go_live_incomplete_checklist',
                'notify_request_to_go_live_incomplete_email_reply_to',
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
                'notify_request_to_go_live',
                'notify_request_to_go_live_complete',
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
                'notify_request_to_go_live',
                'notify_request_to_go_live_incomplete',
                'notify_request_to_go_live_incomplete_checklist',
                'notify_request_to_go_live_incomplete_sms_sender',
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
                'notify_request_to_go_live',
                'notify_request_to_go_live_incomplete',
                'notify_request_to_go_live_incomplete_checklist',
                'notify_request_to_go_live_incomplete_team_member',
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
                'notify_request_to_go_live',
                'notify_request_to_go_live_incomplete',
                'notify_request_to_go_live_incomplete_checklist',
                'notify_request_to_go_live_incomplete_template_content',
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
                'notify_request_to_go_live',
                'notify_request_to_go_live_incomplete',
                'notify_request_to_go_live_incomplete_volumes',
                'notify_request_to_go_live_incomplete_checklist',
                'notify_request_to_go_live_incomplete_mou',
                'notify_request_to_go_live_incomplete_team_member',
                'notify_request_to_go_live_incomplete_template_content',
            ],
        ),
    ),
)
def test_ready_to_go_live(
    client_request,
    mocker,
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

    assert list(app.main.views.service_settings._get_request_to_go_live_tags(
        app.models.service.Service({'id': SERVICE_ONE_ID}),
        agreement_signed,
    )) == expected_tags


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
        mock_get_service_organisation,
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
        service_one)


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
        mock_get_service_organisation,
        single_sms_sender,
        route,
        mock_get_service_settings_page_common,
        mock_get_service_templates,
):
    validate_route_permission(mocker,
                              app_,
                              "GET",
                              200,
                              url_for(route, service_id=service_one['id']),
                              [],
                              platform_admin_user,
                              service_one)


def test_and_more_hint_appears_on_settings_with_more_than_just_a_single_sender(
        client_request,
        service_one,
        multiple_reply_to_email_addresses,
        multiple_letter_contact_blocks,
        mock_get_service_organisation,
        multiple_sms_senders,
        mock_get_service_settings_page_common,
):
    service_one['permissions'] = ['email', 'sms', 'letter']

    page = client_request.get(
        'main.service_settings',
        service_id=service_one['id']
    )

    def get_row(page, index):
        return normalize_spaces(
            page.select('tbody tr')[index].text
        )

    assert get_row(page, 3) == "Email reply-to addresses test@example.com …and 2 more Manage"
    assert get_row(page, 6) == "Text message sender Example …and 2 more Manage"
    assert get_row(page, 11) == "Sender addresses 1 Example Street …and 2 more Manage"


@pytest.mark.parametrize('sender_list_page, expected_output', [
    ('main.service_email_reply_to', 'test@example.com (default) Change'),
    ('main.service_letter_contact_details', '1 Example Street (default) Change'),
    ('main.service_sms_senders', 'GOVUK (default) Change')
])
def test_api_ids_dont_show_on_option_pages_with_a_single_sender(
    client_request,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_service_organisation,
    single_sms_sender,
    sender_list_page,
    expected_output
):
    rows = client_request.get(
        sender_list_page,
        service_id=SERVICE_ONE_ID
    ).select(
        '.user-list-item'
    )

    assert normalize_spaces(rows[0].text) == expected_output
    assert len(rows) == 1


@pytest.mark.parametrize(
    'sender_list_page, \
    sample_data, \
    expected_default_sender_output, \
    expected_second_sender_output, \
    expected_third_sender_output',
    [(
        'main.service_email_reply_to',
        multiple_reply_to_email_addresses,
        'test@example.com (default) Change 1234',
        'test2@example.com Change 5678',
        'test3@example.com Change 9457'
    ), (
        'main.service_letter_contact_details',
        multiple_letter_contact_blocks,
        '1 Example Street (default) Change 1234',
        '2 Example Street Change 5678',
        '3 Example Street Change 9457'
    ), (
        'main.service_sms_senders',
        multiple_sms_senders,
        'Example (default and receives replies) Change 1234',
        'Example 2 Change 5678',
        'Example 3 Change 9457'
    ),
    ]
)
def test_default_option_shows_for_default_sender(
    client_request,
    mocker,
    sender_list_page,
    sample_data,
    expected_default_sender_output,
    expected_second_sender_output,
    expected_third_sender_output
):
    sample_data(mocker)

    rows = client_request.get(
        sender_list_page,
        service_id=SERVICE_ONE_ID
    ).select(
        '.user-list-item'
    )

    assert normalize_spaces(rows[0].text) == expected_default_sender_output
    assert normalize_spaces(rows[1].text) == expected_second_sender_output
    assert normalize_spaces(rows[2].text) == expected_third_sender_output
    assert len(rows) == 3


@pytest.mark.parametrize('sender_list_page, sample_data, expected_output', [
    (
        'main.service_email_reply_to',
        no_reply_to_email_addresses,
        'You haven’t added any email reply-to addresses yet'
    ),
    (
        'main.service_letter_contact_details',
        no_letter_contact_blocks,
        'You haven’t added any letter contact details yet'
    ),
    (
        'main.service_sms_senders',
        no_sms_senders,
        'You haven’t added any text message senders yet'
    ),
])
def test_no_senders_message_shows(
    client_request,
    sender_list_page,
    expected_output,
    sample_data,
    mocker
):
    sample_data(mocker)

    rows = client_request.get(
        sender_list_page,
        service_id=SERVICE_ONE_ID
    ).select(
        '.user-list-item'
    )

    assert normalize_spaces(rows[0].text) == expected_output
    assert len(rows) == 1


@pytest.mark.parametrize('reply_to_input, expected_error', [
    ('', 'Can’t be empty'),
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
    ('', 'Can’t be empty'),
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
    ('', 'Can’t be empty'),
    ('abcdefghijkhgkg', 'Enter 11 characters or fewer'),
    (r' ¯\_(ツ)_/¯ ', 'Use letters and numbers only'),
    ('blood.co.uk', None),
    ('00123', "Can't start with 00")
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


@pytest.mark.parametrize('fixture, data, api_default_args', [
    (no_reply_to_email_addresses, {}, True),
    (multiple_reply_to_email_addresses, {}, False),
    (multiple_reply_to_email_addresses, {"is_default": "y"}, True)
])
def test_add_reply_to_email_address(
    fixture,
    data,
    api_default_args,
    mocker,
    client_request,
    mock_add_reply_to_email_address
):
    fixture(mocker)
    data['email_address'] = "test@example.com"
    client_request.post(
        'main.service_add_email_reply_to',
        service_id=SERVICE_ONE_ID,
        _data=data
    )

    mock_add_reply_to_email_address.assert_called_once_with(
        SERVICE_ONE_ID,
        email_address="test@example.com",
        is_default=api_default_args
    )


@pytest.mark.parametrize('fixture, data, api_default_args', [
    (no_letter_contact_blocks, {}, True),
    (multiple_letter_contact_blocks, {}, False),
    (multiple_letter_contact_blocks, {"is_default": "y"}, True)
])
def test_add_letter_contact(
    fixture,
    data,
    api_default_args,
    mocker,
    client_request,
    mock_add_letter_contact
):
    fixture(mocker)
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
):
    data = {
        'letter_contact_block': "1 Example Street"
    }

    page = client_request.post(
        'main.service_add_letter_contact',
        service_id=SERVICE_ONE_ID,
        _data=data,
        from_template=fake_uuid,
        _follow_redirects=True
    )

    mock_add_letter_contact.assert_called_once_with(
        SERVICE_ONE_ID,
        contact_block="1 Example Street",
        is_default=True
    )

    assert page.find('h1').text == 'Set letter contact block'


@pytest.mark.parametrize('fixture, data, api_default_args', [
    (no_sms_senders, {}, True),
    (multiple_sms_senders, {}, False),
    (multiple_sms_senders, {"is_default": "y"}, True)
])
def test_add_sms_sender(
    fixture,
    data,
    api_default_args,
    mocker,
    client_request,
    mock_add_sms_sender
):
    fixture(mocker)
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


@pytest.mark.parametrize('sender_page, fixture, checkbox_present', [
    ('main.service_add_email_reply_to', no_reply_to_email_addresses, False),
    ('main.service_add_email_reply_to', multiple_reply_to_email_addresses, True),
    ('main.service_add_letter_contact', no_letter_contact_blocks, False),
    ('main.service_add_letter_contact', multiple_letter_contact_blocks, True)
])
def test_default_box_doesnt_show_on_first_sender(
    sender_page,
    fixture,
    mocker,
    checkbox_present,
    client_request
):
    fixture(mocker)
    page = client_request.get(
        sender_page,
        service_id=SERVICE_ONE_ID
    )

    assert bool(page.select_one('[name=is_default]')) == checkbox_present


@pytest.mark.parametrize('fixture, data, api_default_args', [
    (get_default_reply_to_email_address, {"is_default": "y"}, True),
    (get_default_reply_to_email_address, {}, True),
    (get_non_default_reply_to_email_address, {}, False),
    (get_non_default_reply_to_email_address, {"is_default": "y"}, True)
])
def test_edit_reply_to_email_address(
    fixture,
    data,
    api_default_args,
    mocker,
    fake_uuid,
    client_request,
    mock_update_reply_to_email_address
):
    fixture(mocker)
    data['email_address'] = "test@example.gov.uk"
    client_request.post(
        'main.service_edit_email_reply_to',
        service_id=SERVICE_ONE_ID,
        reply_to_email_id=fake_uuid,
        _data=data
    )

    mock_update_reply_to_email_address.assert_called_once_with(
        SERVICE_ONE_ID,
        reply_to_email_id=fake_uuid,
        email_address="test@example.gov.uk",
        is_default=api_default_args
    )


@pytest.mark.parametrize('fixture, expected_link_text, partial_href', [
    (
        get_non_default_reply_to_email_address,
        'Delete',
        partial(url_for, 'main.service_confirm_delete_email_reply_to', reply_to_email_id=sample_uuid()),
    ),
    (
        get_default_reply_to_email_address,
        'Back',
        partial(url_for, '.service_email_reply_to'),
    ),
])
def test_shows_delete_link_for_email_reply_to_address(
    mocker,
    fixture,
    expected_link_text,
    partial_href,
    fake_uuid,
    client_request,
):

    fixture(mocker)

    page = client_request.get(
        'main.service_edit_email_reply_to',
        service_id=SERVICE_ONE_ID,
        reply_to_email_id=sample_uuid(),
    )

    last_link = page.select('.page-footer a')[-1]

    assert normalize_spaces(last_link.text) == expected_link_text
    assert last_link['href'] == partial_href(service_id=SERVICE_ONE_ID)


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
        'Are you sure you want to delete this email reply-to address? '
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


@pytest.mark.parametrize('fixture, data, api_default_args', [
    (get_default_letter_contact_block, {"is_default": "y"}, True),
    (get_default_letter_contact_block, {}, True),
    (get_non_default_letter_contact_block, {}, False),
    (get_non_default_letter_contact_block, {"is_default": "y"}, True)
])
def test_edit_letter_contact_block(
    fixture,
    data,
    api_default_args,
    mocker,
    fake_uuid,
    client_request,
    mock_update_letter_contact
):
    fixture(mocker)
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


@pytest.mark.parametrize('fixture, data, api_default_args', [
    (get_default_sms_sender, {"is_default": "y", "sms_sender": "test"}, True),
    (get_default_sms_sender, {"sms_sender": "test"}, True),
    (get_non_default_sms_sender, {"sms_sender": "test"}, False),
    (get_non_default_sms_sender, {"is_default": "y", "sms_sender": "test"}, True)
])
def test_edit_sms_sender(
    fixture,
    data,
    api_default_args,
    mocker,
    fake_uuid,
    client_request,
    mock_update_sms_sender
):
    fixture(mocker)
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


@pytest.mark.parametrize('sender_page, fixture, default_message, params, checkbox_present', [
    (
        'main.service_edit_email_reply_to',
        get_default_reply_to_email_address,
        'This is the default reply-to address for service one emails',
        'reply_to_email_id',
        False
    ),
    (
        'main.service_edit_email_reply_to',
        get_non_default_reply_to_email_address,
        'This is the default reply-to address for service one emails',
        'reply_to_email_id',
        True
    ),
    (
        'main.service_edit_letter_contact',
        get_default_letter_contact_block,
        'This is currently your default address for service one',
        'letter_contact_id',
        False
    ),
    (
        'main.service_edit_letter_contact',
        get_non_default_letter_contact_block,
        'This is the default contact details for service one letters',
        'letter_contact_id',
        True
    ),
    (
        'main.service_edit_sms_sender',
        get_default_sms_sender,
        'This is the default text message sender',
        'sms_sender_id',
        False
    ),
    (
        'main.service_edit_sms_sender',
        get_non_default_sms_sender,
        'This is the default text message sender',
        'sms_sender_id',
        True
    )
])
def test_default_box_shows_on_non_default_sender_details_while_editing(
    fixture,
    fake_uuid,
    mocker,
    sender_page,
    client_request,
    default_message,
    checkbox_present,
    params
):
    page_arguments = {
        'service_id': SERVICE_ONE_ID
    }
    page_arguments[params] = fake_uuid

    fixture(mocker)
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


@pytest.mark.parametrize('fixture, expected_link_text, partial_href', [
    (
        get_non_default_sms_sender,
        'Delete',
        partial(url_for, 'main.service_confirm_delete_sms_sender', sms_sender_id=sample_uuid()),
    ),
    (
        get_default_sms_sender,
        'Back',
        partial(url_for, '.service_sms_senders'),
    ),
])
def test_shows_delete_link_for_sms_sender(
    mocker,
    fixture,
    expected_link_text,
    partial_href,
    fake_uuid,
    client_request,
):

    fixture(mocker)

    page = client_request.get(
        'main.service_edit_sms_sender',
        service_id=SERVICE_ONE_ID,
        sms_sender_id=sample_uuid(),
    )

    last_link = page.select('.page-footer a')[-1]

    assert normalize_spaces(last_link.text) == expected_link_text
    assert last_link['href'] == partial_href(service_id=SERVICE_ONE_ID)


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


@pytest.mark.parametrize('fixture, expected_link_text', [
    (get_inbound_number_sms_sender, 'Back'),
    (get_default_sms_sender, 'Back'),
    (get_non_default_sms_sender, 'Delete'),
])
def test_inbound_sms_sender_is_not_deleteable(
    client_request,
    service_one,
    fake_uuid,
    fixture,
    expected_link_text,
    mocker
):
    fixture(mocker)

    page = client_request.get(
        '.service_edit_sms_sender',
        service_id=SERVICE_ONE_ID,
        sms_sender_id='1234',
    )

    last_link = page.select('.page-footer a')[-1]
    assert normalize_spaces(last_link.text) == expected_link_text


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
        sms_sender_id='1234',
        _expected_redirect=url_for(
            'main.service_sms_senders',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )
    mock_delete.assert_called_once_with(service_id=SERVICE_ONE_ID, sms_sender_id='1234')


@pytest.mark.parametrize('fixture, hide_textbox, fixture_sender_id', [
    (get_inbound_number_sms_sender, True, '1234'),
    (get_default_sms_sender, False, '1234'),
])
def test_inbound_sms_sender_is_not_editable(
    client_request,
    service_one,
    fake_uuid,
    fixture,
    hide_textbox,
    fixture_sender_id,
    mocker
):
    fixture(mocker)

    page = client_request.get(
        '.service_edit_sms_sender',
        service_id=SERVICE_ONE_ID,
        sms_sender_id=fixture_sender_id,
    )

    assert bool(page.find('input', attrs={'name': "sms_sender"})) != hide_textbox
    if hide_textbox:
        assert normalize_spaces(
            page.select_one('form[method="post"] p').text
        ) == "GOVUK This phone number receives replies and can’t be changed"


def test_shows_research_mode_indicator(
    client_request,
    service_one,
    mocker,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_service_organisation,
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
    mock_get_service_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    page = client_request.get(
        'main.service_settings',
        service_id=SERVICE_ONE_ID,
    )

    element = page.find('span', {"id": "research-mode"})
    assert not element


@pytest.mark.parametrize('method', ['get', 'post'])
def test_cant_set_letter_contact_block_if_service_cant_send_letters(
    client_request,
    service_one,
    method,
):
    assert 'letter' not in service_one['permissions']
    getattr(client_request, method)(
        'main.service_set_letter_contact_block',
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


def test_set_letter_contact_block_prepopulates(
    client_request,
    service_one,
):
    service_one['permissions'] = ['letter']
    service_one['letter_contact_block'] = 'foo bar baz waz'
    page = client_request.get(
        'main.service_set_letter_contact_block',
        service_id=SERVICE_ONE_ID,
    )
    assert 'foo bar baz waz' in page.text


def test_set_letter_contact_block_saves(
    client_request,
    service_one,
    mock_update_service,
):
    service_one['permissions'] = ['letter']
    client_request.post(
        'main.service_set_letter_contact_block',
        service_id=SERVICE_ONE_ID,
        _data={'letter_contact_block': 'foo bar baz waz'},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_settings',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )
    mock_update_service.assert_called_once_with(SERVICE_ONE_ID, letter_contact_block='foo bar baz waz')


def test_set_letter_contact_block_redirects_to_template(
    client_request,
    service_one,
    mock_update_service,
):
    service_one['permissions'] = ['letter']
    client_request.post(
        'main.service_set_letter_contact_block',
        service_id=SERVICE_ONE_ID,
        from_template=FAKE_TEMPLATE_ID,
        _data={'letter_contact_block': '23 Whitechapel Road'},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.view_template',
            service_id=service_one['id'],
            template_id=FAKE_TEMPLATE_ID,
            _external=True,
        ),
    )


def test_set_letter_contact_block_has_max_10_lines(
    client_request,
    service_one,
    mock_update_service,
):
    service_one['permissions'] = ['letter']
    page = client_request.post(
        'main.service_set_letter_contact_block',
        service_id=SERVICE_ONE_ID,
        _data={'letter_contact_block': '\n'.join(map(str, range(0, 11)))},
        _expected_status=200,
    )
    error_message = page.find('span', class_='error-message').text.strip()
    assert error_message == 'Contains 11 lines, maximum is 10'


@pytest.mark.parametrize('extra_args, expected_partial_url', (
    (
        {},
        partial(url_for, 'main.service_settings')
    ),
    (
        {'from_template': FAKE_TEMPLATE_ID},
        partial(url_for, 'main.view_template', template_id=FAKE_TEMPLATE_ID)
    ),
))
def test_request_letter_branding(
    client_request,
    mock_get_letter_branding_by_id,
    extra_args,
    expected_partial_url,
):
    request_page = client_request.get(
        'main.request_letter_branding',
        service_id=SERVICE_ONE_ID,
        **extra_args
    )
    assert request_page.select_one('main p').text.strip() == 'Your letters do not have a logo.'
    link_href = request_page.select_one('main a')['href']
    feedback_page = client_request.get_url(link_href)
    assert feedback_page.select_one('textarea').text.strip() == (
        'I would like my own logo on my letter templates.'
    )
    back_link_href = request_page.select('main a')[1]['href']
    assert back_link_href == expected_partial_url(service_id=SERVICE_ONE_ID)


def test_request_letter_branding_if_already_have_branding(
    client_request,
    mock_get_letter_branding_by_id,
    service_one,
):
    service_one['letter_branding'] = uuid4()

    request_page = client_request.get(
        'main.request_letter_branding',
        service_id=SERVICE_ONE_ID,
    )

    mock_get_letter_branding_by_id.assert_called_once_with(service_one['letter_branding'])
    assert request_page.select_one('main p').text.strip() == 'Your letters have the HM Government logo.'


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
            email_branding_id=submitted_value
        )
        assert mock_update_service.called is False
    else:
        raise Exception


@pytest.mark.parametrize('method', ['get', 'post'])
@pytest.mark.parametrize('endpoint', [
    'main.set_organisation_type',
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


def test_should_show_page_to_set_organisation_type(
    logged_in_platform_admin_client,
):
    response = logged_in_platform_admin_client.get(url_for(
        'main.set_organisation_type',
        service_id=SERVICE_ONE_ID
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    labels = page.select('label')
    checked_radio_buttons = page.select('input[checked]')

    assert len(checked_radio_buttons) == 1
    assert checked_radio_buttons[0]['value'] == 'central'

    assert len(labels) == 3
    for index, expected in enumerate((
        'Central government',
        'Local government',
        'NHS',
    )):
        assert normalize_spaces(labels[index].text) == expected


@pytest.mark.parametrize('organisation_type, free_allowance', [
    ('central', 250000),
    ('local', 25000),
    ('nhs', 25000),
    pytest.param('private sector', 1000, marks=pytest.mark.xfail)
])
def test_should_set_organisation_type(
    logged_in_platform_admin_client,
    mock_update_service,
    organisation_type,
    free_allowance,
    mock_create_or_update_free_sms_fragment_limit
):
    response = logged_in_platform_admin_client.post(
        url_for(
            'main.set_organisation_type',
            service_id=SERVICE_ONE_ID,
        ),
        data={
            'organisation_type': organisation_type,
            'organisation': 'organisation-id'
        },
    )
    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=SERVICE_ONE_ID, _external=True)

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        organisation_type=organisation_type,
    )
    mock_create_or_update_free_sms_fragment_limit.assert_called_once_with(SERVICE_ONE_ID, free_allowance)


def test_should_show_page_to_set_sms_allowance(
    logged_in_platform_admin_client,
    mock_get_free_sms_fragment_limit
):
    response = logged_in_platform_admin_client.get(url_for(
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
    logged_in_platform_admin_client,
    given_allowance,
    expected_api_argument,
    mock_get_free_sms_fragment_limit,
    mock_create_or_update_free_sms_fragment_limit,
):

    response = logged_in_platform_admin_client.post(
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
        'It costs between 30p and 76p to send a letter using Notify.',
        'Send letters',
        ['email', 'sms'],
        'False', 'True',
        ['email', 'sms', 'letter'],
    ),
    (
        'letter',
        'It costs between 30p and 76p to send a letter using Notify.',
        'Send letters',
        ['email', 'sms', 'letter'],
        'True', 'False',
        ['email', 'sms'],
    ),
    (
        'sms',
        'You have a free allowance of 250,000 text messages each financial year.',
        'Send text messages',
        [],
        'False', 'True',
        ['sms'],
    ),
    (
        'email',
        'It’s free to send emails through GOV.UK Notify.',
        'Send emails',
        [],
        'False', 'True',
        ['email'],
    ),
    (
        'email',
        'It’s free to send emails through GOV.UK Notify.',
        'Send emails',
        ['email', 'sms', 'letter'],
        'True', 'True',
        ['email', 'sms', 'letter'],
    ),
])
def test_switch_service_enable_letters(
    client_request,
    service_one,
    mocker,
    mock_get_free_sms_fragment_limit,
    channel,
    expected_first_para,
    expected_legend,
    expected_initial_value,
    posted_value,
    initial_permissions,
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


@pytest.mark.parametrize('start_permissions, contact_details, end_permissions', [
    (['upload_document'], 'http://example.com/', []),
    ([], '0207 123 4567', ['upload_document']),
])
def test_service_switch_can_upload_document_shows_permission_page_if_service_contact_details_exist(
    logged_in_platform_admin_client,
    service_one,
    mock_update_service,
    mock_get_service_settings_page_common,
    mock_get_service_organisation,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    start_permissions,
    contact_details,
    end_permissions,
):
    service_one['permissions'] = start_permissions
    service_one['contact_link'] = contact_details

    response = logged_in_platform_admin_client.get(
        url_for('main.service_switch_can_upload_document', service_id=SERVICE_ONE_ID),
        follow_redirects=True
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert normalize_spaces(page.h1.text) == 'Uploading documents'


def test_service_switch_can_upload_document_turning_permission_on_with_no_contact_details_shows_form(
    logged_in_platform_admin_client,
    service_one,
    mock_get_service_settings_page_common,
    mock_get_service_organisation,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
):
    response = logged_in_platform_admin_client.get(
        url_for('main.service_switch_can_upload_document', service_id=SERVICE_ONE_ID),
        follow_redirects=True
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert 'upload_document' not in service_one['permissions']
    assert normalize_spaces(page.h1.text) == "Add contact details for ‘Download your document’ page"


@pytest.mark.parametrize('contact_details_type, contact_details_value', [
    ('url', 'http://example.com/'),
    ('email_address', 'old@example.com'),
    ('phone_number', '0207 12345'),
])
def test_service_switch_can_upload_document_lets_contact_details_be_added_and_shows_permission_page(
    logged_in_platform_admin_client,
    service_one,
    mock_update_service,
    mock_get_service_settings_page_common,
    mock_get_service_organisation,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    contact_details_type,
    contact_details_value,
):
    data = {'contact_details_type': contact_details_type, contact_details_type: contact_details_value}

    response = logged_in_platform_admin_client.post(
        url_for('main.service_switch_can_upload_document', service_id=SERVICE_ONE_ID),
        data=data,
        follow_redirects=True
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(page.h1.text) == 'Uploading documents'


def test_archive_service_after_confirm(
    logged_in_platform_admin_client,
    service_one,
    mocker,
    mock_get_inbound_number_for_service,
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
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_service_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common,
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
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_service_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common
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
    mock_get_inbound_number_for_service,
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
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_service_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common,
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
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_service_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    service_one['active'] = False

    response = logged_in_platform_admin_client.get(url_for('main.service_settings', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Suspend service' not in {a.text for a in page.find_all('a', class_='button')}


def test_resume_service_after_confirm(
    logged_in_platform_admin_client,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_service_organisation,
    mocker,
    mock_get_inbound_number_for_service,
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
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_service_organisation,
    single_sms_sender,
    mocker,
    mock_get_service_settings_page_common,
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
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_service_organisation,
    single_sms_sender,
    mock_get_service_settings_page_common
):
    response = logged_in_platform_admin_client.get(url_for('main.service_settings', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Resume service' not in {a.text for a in page.find_all('a', class_='button')}


@pytest.mark.parametrize('contact_details_type, contact_details_value', [
    ('url', 'http://example.com/'),
    ('email_address', 'me@example.com'),
    ('phone_number', '0207 123 4567'),
])
def test_service_set_contact_link_prefills_the_form_with_the_existing_contact_details(
    client_request,
    service_one,
    contact_details_type,
    contact_details_value,
):
    service_one['contact_link'] = contact_details_value

    page = client_request.get(
        'main.service_set_contact_link', service_id=SERVICE_ONE_ID
    )
    assert page.find('input', attrs={'name': 'contact_details_type', 'value': contact_details_type}).has_attr('checked')
    assert page.find('input', {'id': contact_details_type}).get('value') == contact_details_value


@pytest.mark.parametrize('contact_details_type, old_value, new_value', [
    ('url', 'http://example.com/', 'http://new-link.com/'),
    ('email_address', 'old@example.com', 'new@example.com'),
    ('phone_number', '0207 12345', '0207 56789'),
])
def test_service_set_contact_link_updates_contact_details_and_redirects_to_settings_page(
    client_request,
    service_one,
    mock_update_service,
    mock_get_service_settings_page_common,
    mock_get_service_organisation,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    contact_details_type,
    old_value,
    new_value,
):
    service_one['contact_link'] = old_value

    page = client_request.post(
        'main.service_set_contact_link', service_id=SERVICE_ONE_ID,
        _data={
            'contact_details_type': contact_details_type,
            contact_details_type: new_value,
        },
        _follow_redirects=True
    )

    assert page.h1.text == 'Settings'
    mock_update_service.assert_called_once_with(SERVICE_ONE_ID, contact_link=new_value)


def test_service_set_contact_link_updates_contact_details_for_the_selected_field_when_multiple_textboxes_contain_data(
    client_request,
    service_one,
    mock_update_service,
    mock_get_service_settings_page_common,
    mock_get_service_organisation,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
):
    service_one['contact_link'] = 'http://www.old-url.com'

    page = client_request.post(
        'main.service_set_contact_link', service_id=SERVICE_ONE_ID,
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


def test_service_set_contact_link_displays_error_message_when_no_radio_button_selected(
    client_request,
    service_one
):
    page = client_request.post(
        'main.service_set_contact_link', service_id=SERVICE_ONE_ID,
        _data={
            'contact_details_type': None,
            'url': '',
            'email_address': '',
            'phone_number': '',
        },
        _follow_redirects=True
    )
    assert normalize_spaces(page.find('span', class_='error-message').text) == 'Not a valid choice'
    assert normalize_spaces(page.h1.text) == "Add contact details for ‘Download your document’ page"


@pytest.mark.parametrize('contact_details_type, invalid_value, error', [
    ('url', 'invalid.com/', 'Must be a valid URL'),
    ('email_address', 'me@co', 'Enter a valid email address'),
    ('phone_number', 'abcde', 'Must be a valid phone number'),
])
def test_service_set_contact_link_does_not_update_invalid_contact_details(
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
        'main.service_set_contact_link', service_id=SERVICE_ONE_ID,
        _data={
            'contact_details_type': contact_details_type,
            contact_details_type: invalid_value,
        },
        _follow_redirects=True
    )

    assert normalize_spaces(page.find('span', class_='error-message').text) == error
    assert normalize_spaces(page.h1.text) == "Change contact details for ‘Download your document’ page"


def test_contact_link_is_displayed_with_upload_document_permission(
    client_request,
    service_one,
    mock_get_service_settings_page_common,
    mock_get_service_organisation,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
):
    service_one['permissions'] = ['upload_document']
    page = client_request.get(
        'main.service_settings',
        service_id=SERVICE_ONE_ID,
    )
    assert 'Contact details' in page.text


def test_contact_link_is_not_displayed_without_the_upload_document_permission(
    client_request,
    service_one,
    mock_get_service_settings_page_common,
    mock_get_service_organisation,
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
            'If you want to be able to receive text messages from your users, please get in touch.'
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
    mock_get_service_organisation,
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
    (active_user_with_permissions, [
        'Your service can receive text messages sent to 07700900123.',
        'If you want to turn this feature off, get in touch with the GOV.UK Notify team.',
        'You can set up callbacks for received text messages on the API integration page.',
    ]),
    (active_user_no_api_key_permission, [
        'Your service can receive text messages sent to 07700900123.',
        'If you want to turn this feature off, get in touch with the GOV.UK Notify team.',
    ]),
])
def test_set_inbound_sms_when_inbound_number_is_set(
    client_request,
    service_one,
    mocker,
    fake_uuid,
    user,
    expected_paragraphs,
):
    service_one['permissions'] = ['inbound_sms']
    mocker.patch('app.inbound_number_client.get_inbound_sms_number_for_service', return_value={
        'data': {'number': '07700900123'}
    })
    client_request.login(user(fake_uuid))
    page = client_request.get(
        'main.service_set_inbound_sms',
        service_id=SERVICE_ONE_ID,
    )
    paragraphs = page.select('main p')

    assert len(paragraphs) == len(expected_paragraphs)

    for index, p in enumerate(expected_paragraphs):
        assert normalize_spaces(paragraphs[index].text) == p


def test_empty_letter_contact_block_returns_error(
    client_request,
    service_one,
    mock_update_service,
):
    service_one['permissions'] = ['letter']
    page = client_request.post(
        'main.service_set_letter_contact_block',
        service_id=SERVICE_ONE_ID,
        _data={'letter_contact_block': None},
        _expected_status=200,
    )
    error_message = page.find('span', class_='error-message').text.strip()
    assert error_message == 'Can’t be empty'


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
    logged_in_platform_admin_client,
    service_one,
    mock_get_service_organisation,
    mock_get_organisations
):
    response = logged_in_platform_admin_client.get(
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
    logged_in_platform_admin_client,
    service_one,
    mock_get_service_organisation,
    mocker
):
    mocker.patch('app.organisations_client.get_organisations', return_value=[])

    response = logged_in_platform_admin_client.get(
        url_for('.link_service_to_organisation', service_id=service_one['id']),
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(page.select_one('main p').text) == "No organisations"
    assert not page.select_one('main button')


def test_update_service_organisation(
    logged_in_platform_admin_client,
    service_one,
    mock_get_service_organisation,
    mock_get_organisations,
    mock_update_service_organisation,
):
    response = logged_in_platform_admin_client.post(
        url_for('.link_service_to_organisation', service_id=service_one['id']),
        data={'organisations': '7aa5d4e9-4385-4488-a489-07812ba13384'},
    )

    assert response.status_code == 302
    mock_update_service_organisation.assert_called_once_with(
        service_one['id'],
        '7aa5d4e9-4385-4488-a489-07812ba13384'
    )


def test_update_service_organisation_does_not_update_if_same_value(
    logged_in_platform_admin_client,
    service_one,
    mock_get_service_organisation,
    mock_get_organisations,
    mock_update_service_organisation,
):
    response = logged_in_platform_admin_client.post(
        url_for('.link_service_to_organisation', service_id=service_one['id']),
        data={'organisations': '7aa5d4e9-4385-4488-a489-07812ba13383'},
    )

    assert response.status_code == 302
    mock_update_service_organisation.called is False


def test_show_email_branding_request_page_when_no_email_branding_is_set(
    client_request,
    mock_get_email_branding
):
    page = client_request.get(
        '.branding_request', service_id=SERVICE_ONE_ID
    )

    mock_get_email_branding.assert_not_called()

    radios = page.select('input[type=radio]')

    for index, option in enumerate((
        'govuk',
        'both',
        'org',
        'org_banner',
    )):
        assert radios[index]['name'] == 'options'
        assert radios[index]['value'] == option


def test_show_email_branding_request_page_when_email_branding_is_set(
    client_request,
    mock_get_email_branding,
    active_user_with_permissions,
):

    service_one = service_json(email_branding='1234')
    client_request.login(active_user_with_permissions, service=service_one)

    page = client_request.get(
        '.branding_request', service_id=SERVICE_ONE_ID
    )

    mock_get_email_branding.called_once_with('1234')

    radios = page.select('input[type=radio]')

    for index, option in enumerate((
        'govuk',
        'both',
        'org',
        'org_banner',
    )):
        assert radios[index]['name'] == 'options'
        assert radios[index]['value'] == option
        if option == 'org':
            assert 'checked' in radios[index].attrs


@pytest.mark.parametrize('choice, requested_branding', (
    ('govuk', 'GOV.UK only'),
    ('both', 'GOV.UK and logo'),
    ('org', 'Your logo'),
    ('org_banner', 'Your logo on a colour'),
    pytest.param('foo', 'Nope', marks=pytest.mark.xfail(raises=AssertionError)),
))
def test_submit_email_branding_request(
    client_request,
    mocker,
    choice,
    requested_branding,
    mock_get_service_settings_page_common,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    mock_get_service_organisation,
    single_sms_sender,
):

    zendesk = mocker.patch(
        'app.main.views.service_settings.zendesk_client.create_ticket',
        autospec=True,
    )

    page = client_request.post(
        '.branding_request', service_id=SERVICE_ONE_ID,
        _data={
            'options': choice,
        },
        _follow_redirects=True,
    )

    zendesk.assert_called_once_with(
        message='\n'.join([
            'Organisation: Can’t tell (domain is user.gov.uk)',
            'Service: service one',
            'http://localhost/services/596364a0-858e-42c8-9062-a8fe822260eb',
            '',
            '---',
            'Current branding: GOV.UK',
            'Branding requested: {}',
        ]).format(requested_branding),
        subject='Email branding request - service one',
        ticket_type='question',
        user_email='test@user.gov.uk',
        user_name='Test User',
        tags=['notify_action_add_branding'],
    )
    assert normalize_spaces(page.select_one('.banner-default').text) == (
        'Thanks for your branding request. We’ll get back to you '
        'within one working day.'
    )


def test_show_service_data_retention(
        logged_in_platform_admin_client,
        service_one,
        mock_get_service_data_retention,

):

    mock_get_service_data_retention.return_value[0]['days_of_retention'] = 5

    response = logged_in_platform_admin_client.get(url_for('main.data_retention', service_id=service_one['id']))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    rows = page.select('tbody tr')
    assert len(rows) == 1
    assert normalize_spaces(rows[0].text) == 'Email 5 Change'


def test_view_add_service_data_retention(
        logged_in_platform_admin_client,
        service_one,

):
    response = logged_in_platform_admin_client.get(url_for('main.add_data_retention', service_id=service_one['id']))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert normalize_spaces(page.select_one('input')['value']) == "email"
    assert page.find('input', attrs={'name': 'days_of_retention'})


def test_add_service_data_retention(
        logged_in_platform_admin_client,
        service_one,
        mock_create_service_data_retention
):
    response = logged_in_platform_admin_client.post(url_for('main.add_data_retention', service_id=service_one['id']),
                                                    data={'notification_type': "email",
                                                          'days_of_retention': 5
                                                          }
                                                    )
    assert response.status_code == 302
    settings_url = url_for(
        'main.data_retention', service_id=service_one['id'], _external=True)
    assert settings_url == response.location
    assert mock_create_service_data_retention.called


def test_update_service_data_retention(
        logged_in_platform_admin_client,
        service_one,
        fake_uuid,
        mock_get_service_data_retention,
        mock_update_service_data_retention,
):
    response = logged_in_platform_admin_client.post(url_for('main.edit_data_retention',
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
        logged_in_platform_admin_client,
        service_one,
        fake_uuid,
        mock_get_service_data_retention,
        mock_update_service_data_retention,
):
    response = logged_in_platform_admin_client.post(url_for('main.edit_data_retention',
                                                            service_id=service_one['id'],
                                                            data_retention_id=fake_uuid),
                                                    data={'days_of_retention': -5}
                                                    )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    error_message = page.find('span', class_='error-message').text.strip()
    assert error_message == 'Must be between 3 and 90'
    assert mock_get_service_data_retention.called
    assert not mock_update_service_data_retention.called


def test_update_service_data_retention_populates_form(
        logged_in_platform_admin_client,
        service_one,
        fake_uuid,
        mock_get_service_data_retention,
):

    mock_get_service_data_retention.return_value[0]['days_of_retention'] = 5
    response = logged_in_platform_admin_client.get(url_for('main.edit_data_retention',
                                                           service_id=service_one['id'],
                                                           data_retention_id=fake_uuid)
                                                   )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('input', attrs={'name': 'days_of_retention'})['value'] == '5'
