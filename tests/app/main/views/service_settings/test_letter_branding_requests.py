from unittest.mock import ANY, PropertyMock

import pytest
from flask import url_for
from notifications_utils.clients.zendesk.zendesk_client import (
    NotifySupportTicket,
)

from tests import organisation_json, sample_uuid
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
    TEMPLATE_ONE_ID,
    normalize_spaces,
)


@pytest.mark.parametrize('organisation_type, expected_options', (
    ('nhs_central', [
        ('nhs', 'NHS'),
        ('something_else', 'Something else'),
    ]),
    ('other', None),
))
def test_letter_branding_request_page_when_no_branding_is_set(
    service_one,
    client_request,
    mock_get_email_branding,
    mock_get_letter_branding_by_id,
    organisation_type,
    expected_options,
):
    service_one['letter_branding'] = None
    service_one['organisation_type'] = organisation_type

    page = client_request.get(
        '.letter_branding_request', service_id=SERVICE_ONE_ID
    )

    assert mock_get_email_branding.called is False
    assert mock_get_letter_branding_by_id.called is False

    button_text = normalize_spaces(page.select_one('.page-footer button').text)
    assert button_text == 'Request new branding'

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


@pytest.mark.parametrize('from_template,back_link_url', [
    (None, '/services/{}/service-settings'.format(SERVICE_ONE_ID),),
    (TEMPLATE_ONE_ID, '/services/{}/templates/{}'.format(SERVICE_ONE_ID, TEMPLATE_ONE_ID),)
])
def test_letter_branding_request_page_back_link(
    client_request,
    from_template,
    back_link_url,
):
    if from_template:
        page = client_request.get(
            '.letter_branding_request', service_id=SERVICE_ONE_ID, from_template=from_template
        )
    else:
        page = client_request.get(
            '.letter_branding_request', service_id=SERVICE_ONE_ID
        )

    back_link = page.select('a[class=govuk-back-link]')
    assert back_link[0].attrs['href'] == back_link_url


@pytest.mark.parametrize('org_name, expected_organisation', (
    (None, 'Can’t tell (domain is user.gov.uk)'),
    ('Test Organisation', 'Test Organisation'),
))
def test_letter_branding_request_submit(
    client_request,
    service_one,
    mocker,
    mock_get_letter_branding_by_id,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    org_name,
    expected_organisation,
):
    service_one['letter_branding'] = sample_uuid()
    organisation_id = ORGANISATION_ID if org_name else None

    mocker.patch(
        'app.models.service.Service.organisation_id',
        new_callable=PropertyMock,
        return_value=organisation_id,
    )
    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(name=org_name),
    )

    mock_create_ticket = mocker.spy(NotifySupportTicket, '__init__')
    mock_send_ticket_to_zendesk = mocker.patch(
        'app.main.views.service_settings.zendesk_client.send_ticket_to_zendesk',
        autospec=True,
    )

    page = client_request.post(
        '.letter_branding_request', service_id=SERVICE_ONE_ID,
        _data={
            'options': 'something_else',
            'something_else': 'Homer Simpson',
        },
        _follow_redirects=True,
    )

    mock_create_ticket.assert_called_once_with(
        ANY,
        message='\n'.join([
            'Organisation: {}',
            'Service: service one',
            'http://localhost/services/596364a0-858e-42c8-9062-a8fe822260eb',
            '',
            '---',
            'Current branding: HM Government',
            'Branding requested: Something else\n\nHomer Simpson\n',
        ]).format(expected_organisation),
        subject='Letter branding request - service one',
        ticket_type='question',
        user_name='Test User',
        user_email='test@user.gov.uk',
        org_id=organisation_id,
        org_type='central',
        service_id=SERVICE_ONE_ID
    )
    mock_send_ticket_to_zendesk.assert_called_once()
    assert normalize_spaces(page.select_one('.banner-default').text) == (
        'Thanks for your branding request. We’ll get back to you '
        'within one working day.'
    )


@pytest.mark.parametrize('data, error_message', (
    ({'options': 'something_else'}, 'Cannot be empty'),  # no data in 'something_else' textbox
    ({'options': ''}, 'Select an option'),  # no radio button selected
))
def test_letter_branding_request_submit_when_form_has_missing_data(
    client_request,
    mocker,
    service_one,
    organisation_one,
    data,
    error_message,
    mock_get_letter_branding_by_id,
):
    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_one,
    )
    service_one['letter_branding'] = sample_uuid()
    service_one['organisation'] = organisation_one

    page = client_request.post(
        '.letter_branding_request', service_id=SERVICE_ONE_ID,
        _data=data,
        _follow_redirects=True,
    )
    assert page.h1.text == 'Change letter branding'
    assert normalize_spaces(page.select_one('.error-message').text) == error_message


@pytest.mark.parametrize('from_template', [
    None,
    TEMPLATE_ONE_ID
])
def test_letter_branding_request_submit_redirects_if_from_template_is_set(
    client_request,
    service_one,
    mocker,
    from_template,

):
    mocker.patch('app.main.views.service_settings.zendesk_client.send_ticket_to_zendesk', autospec=True)
    data = {'options': 'something_else', 'something_else': 'Homer Simpson'}

    if from_template:
        client_request.post(
            '.letter_branding_request', service_id=SERVICE_ONE_ID, from_template=from_template,
            _data=data,
            _expected_redirect=url_for(
                'main.view_template', service_id=SERVICE_ONE_ID, template_id=from_template,
            )
        )
    else:
        client_request.post(
            '.letter_branding_request', service_id=SERVICE_ONE_ID,
            _data=data,
            _expected_redirect=url_for('main.service_settings', service_id=SERVICE_ONE_ID)
        )


def test_letter_branding_submit_when_something_else_is_only_option(
    client_request,
    service_one,
    mocker,
    mock_get_letter_branding_by_id,
):
    mock_create_ticket = mocker.spy(NotifySupportTicket, '__init__')
    mocker.patch(
        'app.main.views.service_settings.zendesk_client.send_ticket_to_zendesk',
        autospec=True,
    )

    client_request.post(
        '.letter_branding_request',
        service_id=SERVICE_ONE_ID,
        _data={
            'something_else': 'Homer Simpson',
        },
    )

    assert (
        'Current branding: no\n'
        'Branding requested: Something else\n'
        '\n'
        'Homer Simpson'
    ) in mock_create_ticket.call_args_list[0][1]['message']
