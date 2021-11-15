import pytest
from bs4 import BeautifulSoup
from flask import url_for
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError

from tests import organisation_json, service_json
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
    SERVICE_TWO_ID,
    create_active_user_with_permissions,
    create_platform_admin_user,
    normalize_spaces,
)


def test_organisation_page_shows_all_organisations(
    platform_admin_client,
    mocker
):
    orgs = [
        {'id': 'A3', 'name': 'Test 3', 'active': True, 'count_of_live_services': 0},
        {'id': 'B1', 'name': 'Test 1', 'active': True, 'count_of_live_services': 1},
        {'id': 'C2', 'name': 'Test 2', 'active': False, 'count_of_live_services': 2},
    ]

    get_organisations = mocker.patch(
        'app.models.organisation.AllOrganisations.client_method', return_value=orgs
    )
    response = platform_admin_client.get(
        url_for('.organisations')
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(
        page.select_one('h1').text
    ) == "Organisations"

    assert [
        (
            normalize_spaces(link.text),
            normalize_spaces(hint.text),
            link['href'],
        ) for link, hint in zip(
            page.select('.browse-list-item a'),
            page.select('.browse-list-item .browse-list-hint'),
        )
    ] == [
        ('Test 1', '1 live service', url_for(
            'main.organisation_dashboard', org_id='B1'
        )),
        ('Test 2', '2 live services', url_for(
            'main.organisation_dashboard', org_id='C2'
        )),
        ('Test 3', '0 live services', url_for(
            'main.organisation_dashboard', org_id='A3'
        )),
    ]

    archived = page.select_one('.table-field-status-default.heading-medium')
    assert normalize_spaces(archived.text) == '- archived'
    assert normalize_spaces(archived.parent.text) == 'Test 2 - archived 2 live services'

    assert normalize_spaces(
        page.select_one('a.govuk-button--secondary').text
    ) == 'New organisation'
    get_organisations.assert_called_once_with()


def test_view_organisation_shows_the_correct_organisation(
    client_request,
    mocker
):
    org = {'id': ORGANISATION_ID, 'name': 'Test 1', 'active': True}
    mocker.patch(
        'app.organisations_client.get_organisation', return_value=org
    )
    mocker.patch(
        'app.organisations_client.get_services_and_usage', return_value={'services': {}}
    )

    page = client_request.get(
        '.organisation_dashboard',
        org_id=ORGANISATION_ID,
    )

    assert normalize_spaces(page.select_one('h1').text) == 'Usage'
    assert normalize_spaces(page.select_one('.govuk-hint').text) == (
        'Test 1 has no live services on GOV.UK Notify'
    )


def test_page_to_create_new_organisation(
    client_request,
    platform_admin_user,
    mocker,
):
    client_request.login(platform_admin_user)
    page = client_request.get('.add_organisation')

    assert [
        (input['type'], input['name'], input.get('value'))
        for input in page.select('input')
    ] == [
        ('text', 'name', None),
        ('radio', 'organisation_type', 'central'),
        ('radio', 'organisation_type', 'local'),
        ('radio', 'organisation_type', 'nhs_central'),
        ('radio', 'organisation_type', 'nhs_local'),
        ('radio', 'organisation_type', 'nhs_gp'),
        ('radio', 'organisation_type', 'emergency_service'),
        ('radio', 'organisation_type', 'school_or_college'),
        ('radio', 'organisation_type', 'other'),
        ('radio', 'crown_status', 'crown'),
        ('radio', 'crown_status', 'non-crown'),
        ('hidden', 'csrf_token', mocker.ANY),
    ]


def test_create_new_organisation(
    client_request,
    platform_admin_user,
    mocker,
):
    mock_create_organisation = mocker.patch(
        'app.organisations_client.create_organisation',
        return_value=organisation_json(ORGANISATION_ID),
    )

    client_request.login(platform_admin_user)
    client_request.post(
        '.add_organisation',
        _data={
            'name': 'new name',
            'organisation_type': 'local',
            'crown_status': 'non-crown',
        },
        _expected_redirect=url_for(
            'main.organisation_settings',
            org_id=ORGANISATION_ID,
            _external=True,
        ),
    )

    mock_create_organisation.assert_called_once_with(
        name='new name',
        organisation_type='local',
        crown=False,
        agreement_signed=False,
    )


def test_create_new_organisation_validates(
    client_request,
    platform_admin_user,
    mocker,
):
    mock_create_organisation = mocker.patch(
        'app.organisations_client.create_organisation'
    )

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.add_organisation',
        _expected_status=200,
    )
    assert [
        (error['data-error-label'], normalize_spaces(error.text))
        for error in page.select('.govuk-error-message')
    ] == [
        ('name', 'Error: Cannot be empty'),
        ('organisation_type', 'Error: Select the type of organisation'),
        ('crown_status', 'Error: Select whether this organisation is a crown body'),
    ]
    assert mock_create_organisation.called is False


@pytest.mark.parametrize('name, error_message', [
    ('', 'Cannot be empty'),
    ('a', 'at least two alphanumeric characters'),
    ('a' * 256, 'Organisation name must be 255 characters or fewer'),
])
def test_create_new_organisation_fails_with_incorrect_input(
    client_request,
    platform_admin_user,
    mocker,
    name,
    error_message,
):
    mock_create_organisation = mocker.patch(
        'app.organisations_client.create_organisation'
    )

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.add_organisation',
        _data={
            'name': name,
            'organisation_type': 'local',
            'crown_status': 'non-crown',
        },
        _expected_status=200,
    )
    assert mock_create_organisation.called is False
    assert error_message in page.select_one('.govuk-error-message').text


def test_create_new_organisation_fails_with_duplicate_name(
    client_request,
    platform_admin_user,
    mocker,
):
    def _create(**_kwargs):
        json_mock = mocker.Mock(return_value={'message': 'Organisation name already exists'})
        resp_mock = mocker.Mock(status_code=400, json=json_mock)
        http_error = HTTPError(response=resp_mock, message="Default message")
        raise http_error

    mocker.patch(
        'app.organisations_client.create_organisation',
        side_effect=_create
    )

    client_request.login(platform_admin_user)
    page = client_request.post(
        '.add_organisation',
        _data={
            'name': 'Existing org',
            'organisation_type': 'local',
            'crown_status': 'non-crown',
        },
        _expected_status=200,
    )

    error_message = 'This organisation name is already in use'
    assert error_message in page.select_one('.govuk-error-message').text


@pytest.mark.parametrize('organisation_type, organisation, expected_status', (
    ('nhs_gp', None, 200),
    ('central', None, 403),
    ('nhs_gp', organisation_json(organisation_type='nhs_gp'), 403),
))
def test_gps_can_create_own_organisations(
    client_request,
    mocker,
    mock_get_service_organisation,
    service_one,
    organisation_type,
    organisation,
    expected_status,
):
    mocker.patch('app.organisations_client.get_organisation', return_value=organisation)
    service_one['organisation_type'] = organisation_type

    page = client_request.get(
        '.add_organisation_from_gp_service',
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_status,
    )

    if expected_status == 403:
        return

    assert page.select_one('input[type=text]')['name'] == 'name'
    assert normalize_spaces(
        page.select_one('label[for=name]').text
    ) == (
        'What’s your practice called?'
    )


@pytest.mark.parametrize('organisation_type, organisation, expected_status', (
    ('nhs_local', None, 200),
    ('nhs_gp', None, 403),
    ('central', None, 403),
    ('nhs_local', organisation_json(organisation_type='nhs_local'), 403),
))
def test_nhs_local_can_create_own_organisations(
    client_request,
    mocker,
    mock_get_service_organisation,
    service_one,
    organisation_type,
    organisation,
    expected_status,
):
    mocker.patch('app.organisations_client.get_organisation', return_value=organisation)
    mocker.patch(
        'app.models.organisation.AllOrganisations.client_method',
        return_value=[
            organisation_json('t2', 'Trust 2', organisation_type='nhs_local'),
            organisation_json('t1', 'Trust 1', organisation_type='nhs_local'),
            organisation_json('gp1', 'GP 1', organisation_type='nhs_gp'),
            organisation_json('c1', 'Central 1'),
        ],
    )
    service_one['organisation_type'] = organisation_type

    page = client_request.get(
        '.add_organisation_from_nhs_local_service',
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_status,
    )

    if expected_status == 403:
        return

    assert normalize_spaces(page.select_one('main p').text) == (
        'Which NHS Trust or Clinical Commissioning Group do you work for?'
    )
    assert page.select_one('[data-module=live-search]')['data-targets'] == (
        '.govuk-radios__item'
    )
    assert [
        (
            normalize_spaces(radio.select_one('label').text),
            radio.select_one('input')['value']
        )
        for radio in page.select('.govuk-radios__item')
    ] == [
        ('Trust 1', 't1'),
        ('Trust 2', 't2'),
    ]
    assert normalize_spaces(page.select_one('.js-stick-at-bottom-when-scrolling button').text) == (
        'Continue'
    )


@pytest.mark.parametrize('data, expected_service_name', (
    (
        {
            'same_as_service_name': False,
            'name': 'Dr. Example',
        },
        'Dr. Example',
    ),
    (
        {
            'same_as_service_name': True,
            'name': 'This is ignored',
        },
        'service one',
    ),
))
def test_gps_can_name_their_organisation(
    client_request,
    mocker,
    service_one,
    mock_update_service_organisation,
    data,
    expected_service_name,
):
    service_one['organisation_type'] = 'nhs_gp'
    mock_create_organisation = mocker.patch(
        'app.organisations_client.create_organisation',
        return_value=organisation_json(ORGANISATION_ID),
    )

    client_request.post(
        '.add_organisation_from_gp_service',
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_agreement',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )

    mock_create_organisation.assert_called_once_with(
        name=expected_service_name,
        organisation_type='nhs_gp',
        agreement_signed=False,
        crown=False,
    )
    mock_update_service_organisation.assert_called_once_with(SERVICE_ONE_ID, ORGANISATION_ID)


@pytest.mark.parametrize('data, expected_error', (
    (
        {
            'name': 'Dr. Example',
        },
        'Select yes or no',
    ),
    (
        {
            'same_as_service_name': False,
            'name': '',
        },
        'Cannot be empty',
    ),
))
def test_validation_of_gps_creating_organisations(
    client_request,
    mocker,
    service_one,
    data,
    expected_error,
):
    service_one['organisation_type'] = 'nhs_gp'
    page = client_request.post(
        '.add_organisation_from_gp_service',
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=200,
    )
    assert expected_error in page.select_one('.govuk-error-message, .error-message').text


def test_nhs_local_assigns_to_selected_organisation(
    client_request,
    mocker,
    service_one,
    mock_get_organisation,
    mock_update_service_organisation,
):
    mocker.patch(
        'app.models.organisation.AllOrganisations.client_method',
        return_value=[
            organisation_json(ORGANISATION_ID, 'Trust 1', organisation_type='nhs_local'),
        ],
    )
    service_one['organisation_type'] = 'nhs_local'

    client_request.post(
        '.add_organisation_from_nhs_local_service',
        service_id=SERVICE_ONE_ID,
        _data={
            'organisations': ORGANISATION_ID,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_agreement',
            service_id=SERVICE_ONE_ID,
            _external=True
        )
    )
    mock_update_service_organisation.assert_called_once_with(SERVICE_ONE_ID, ORGANISATION_ID)


@freeze_time("2020-02-20 20:20")
def test_organisation_services_shows_live_services_and_usage(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
    fake_uuid,
):
    mock = mocker.patch(
        'app.organisations_client.get_services_and_usage',
        return_value={"services": [
            {'service_id': SERVICE_ONE_ID, 'service_name': '1', 'chargeable_billable_sms': 250122, 'emails_sent': 13000,
             'free_sms_limit': 250000, 'letter_cost': 30.50, 'sms_billable_units': 122, 'sms_cost': 0,
             'sms_remainder': None},
            {'service_id': SERVICE_TWO_ID, 'service_name': '5', 'chargeable_billable_sms': 0, 'emails_sent': 20000,
             'free_sms_limit': 250000, 'letter_cost': 0, 'sms_billable_units': 2500, 'sms_cost': 42.0,
             'sms_remainder': None}
        ]}
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get('.organisation_dashboard', org_id=ORGANISATION_ID)
    mock.assert_called_once_with(ORGANISATION_ID, 2019)

    services = page.select('main h3')
    usage_rows = page.select('main .govuk-grid-column-one-third')
    assert len(services) == 2

    # Totals
    assert normalize_spaces(usage_rows[0].text) == "Emails 33,000 sent"
    assert normalize_spaces(usage_rows[1].text) == "Text messages £42.00 spent"
    assert normalize_spaces(usage_rows[2].text) == "Letters £30.50 spent"

    assert normalize_spaces(services[0].text) == '1'
    assert normalize_spaces(services[1].text) == '5'
    assert services[0].find('a')['href'] == url_for('main.usage', service_id=SERVICE_ONE_ID)

    assert normalize_spaces(usage_rows[3].text) == "13,000 emails sent"
    assert normalize_spaces(usage_rows[4].text) == "122 free text messages sent"
    assert normalize_spaces(usage_rows[5].text) == "£30.50 spent on letters"
    assert services[1].find('a')['href'] == url_for('main.usage', service_id=SERVICE_TWO_ID)
    assert normalize_spaces(usage_rows[6].text) == "20,000 emails sent"
    assert normalize_spaces(usage_rows[7].text) == "£42.00 spent on text messages"
    assert normalize_spaces(usage_rows[8].text) == "£0.00 spent on letters"

    # Ensure there’s no ‘this org has no services message’
    assert not page.select('.govuk-hint')


@freeze_time("2020-02-20 20:20")
def test_organisation_services_shows_live_services_and_usage_with_count_of_1(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
    fake_uuid,
):
    mocker.patch(
        'app.organisations_client.get_services_and_usage',
        return_value={"services": [
            {'service_id': SERVICE_ONE_ID, 'service_name': '1', 'chargeable_billable_sms': 1, 'emails_sent': 1,
             'free_sms_limit': 250000, 'letter_cost': 0, 'sms_billable_units': 1, 'sms_cost': 0,
             'sms_remainder': None},
        ]}
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get('.organisation_dashboard', org_id=ORGANISATION_ID)

    usage_rows = page.select('main .govuk-grid-column-one-third')

    # Totals
    assert normalize_spaces(usage_rows[0].text) == "Emails 1 sent"
    assert normalize_spaces(usage_rows[1].text) == "Text messages £0.00 spent"
    assert normalize_spaces(usage_rows[2].text) == "Letters £0.00 spent"

    assert normalize_spaces(usage_rows[3].text) == "1 email sent"
    assert normalize_spaces(usage_rows[4].text) == "1 free text message sent"
    assert normalize_spaces(usage_rows[5].text) == "£0.00 spent on letters"


@freeze_time("2020-02-20 20:20")
@pytest.mark.parametrize('financial_year, expected_selected', (
    (2017, '2017 to 2018 financial year'),
    (2018, '2018 to 2019 financial year'),
    (2019, '2019 to 2020 financial year'),
))
def test_organisation_services_filters_by_financial_year(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
    fake_uuid,
    financial_year,
    expected_selected,
):
    mock = mocker.patch(
        'app.organisations_client.get_services_and_usage',
        return_value={"services": []}
    )
    page = client_request.get(
        '.organisation_dashboard',
        org_id=ORGANISATION_ID,
        year=financial_year,
    )
    mock.assert_called_once_with(ORGANISATION_ID, financial_year)
    assert normalize_spaces(page.select_one('.pill').text) == (
        '2019 to 2020 financial year '
        '2018 to 2019 financial year '
        '2017 to 2018 financial year'
    )
    assert normalize_spaces(page.select_one('.pill-item--selected').text) == (
        expected_selected
    )


@freeze_time("2020-02-20 20:20")
def test_organisation_services_shows_search_bar(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
    fake_uuid,
):
    mocker.patch(
        'app.organisations_client.get_services_and_usage',
        return_value={"services": [
            {
                'service_id': SERVICE_ONE_ID,
                'service_name': 'Service 1',
                'chargeable_billable_sms': 250122,
                'emails_sent': 13000,
                'free_sms_limit': 250000,
                'letter_cost': 30.50,
                'sms_billable_units': 122,
                'sms_cost': 1.93,
                'sms_remainder': None
            },
        ] * 8}
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get('.organisation_dashboard', org_id=ORGANISATION_ID)

    services = page.select('.organisation-service')
    assert len(services) == 8

    assert page.select_one('.live-search')['data-targets'] == '.organisation-service'
    assert [
        normalize_spaces(service_name.text)
        for service_name in page.select('.live-search-relevant')
    ] == [
        'Service 1',
        'Service 1',
        'Service 1',
        'Service 1',
        'Service 1',
        'Service 1',
        'Service 1',
        'Service 1',
    ]


@freeze_time("2020-02-20 20:20")
def test_organisation_services_hides_search_bar_for_7_or_fewer_services(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
    fake_uuid,
):
    mocker.patch(
        'app.organisations_client.get_services_and_usage',
        return_value={"services": [
            {
                'service_id': SERVICE_ONE_ID,
                'service_name': 'Service 1',
                'chargeable_billable_sms': 250122,
                'emails_sent': 13000,
                'free_sms_limit': 250000,
                'letter_cost': 30.50,
                'sms_billable_units': 122,
                'sms_cost': 1.93,
                'sms_remainder': None
            },
        ] * 7}
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get('.organisation_dashboard', org_id=ORGANISATION_ID)

    services = page.select('.organisation-service')
    assert len(services) == 7
    assert not page.select_one('.live-search')


def test_organisation_trial_mode_services_shows_all_non_live_services(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mocker,
    fake_uuid,
):
    mocker.patch(
        'app.organisations_client.get_organisation_services',
        return_value=[
            service_json(id_='1', name='1', restricted=False, active=True),  # live
            service_json(id_='2', name='2', restricted=True, active=True),  # trial
            service_json(id_='3', name='3', restricted=False, active=False),  # archived
        ]
    )

    client_request.login(platform_admin_user)
    page = client_request.get(
        '.organisation_trial_mode_services',
        org_id=ORGANISATION_ID,
        _test_page_title=False
    )

    services = page.select('.browse-list-item')
    assert len(services) == 2

    assert normalize_spaces(services[0].text) == '2'
    assert normalize_spaces(services[1].text) == '3'
    assert services[0].find('a')['href'] == url_for('main.service_dashboard', service_id='2')
    assert services[1].find('a')['href'] == url_for('main.service_dashboard', service_id='3')


def test_organisation_trial_mode_services_doesnt_work_if_not_platform_admin(
    client_request,
    mock_get_organisation,
):
    client_request.get(
        '.organisation_trial_mode_services',
        org_id=ORGANISATION_ID,
        _expected_status=403
    )


def test_cancel_invited_org_user_cancels_user_invitations(
    client_request,
    mock_get_invites_for_organisation,
    sample_org_invite,
    mock_get_organisation,
    mock_get_users_for_organisation,
    mocker,
):
    mock_cancel = mocker.patch('app.org_invite_api_client.cancel_invited_user')
    mocker.patch('app.org_invite_api_client.get_invited_user_for_org', return_value=sample_org_invite)

    page = client_request.get(
        'main.cancel_invited_org_user',
        org_id=ORGANISATION_ID,
        invited_user_id=sample_org_invite['id'],
        _follow_redirects=True
    )
    assert normalize_spaces(page.h1.text) == 'Team members'
    flash_banner = normalize_spaces(
        page.find('div', class_='banner-default-with-tick').text
    )
    assert flash_banner == f"Invitation cancelled for {sample_org_invite['email_address']}"
    mock_cancel.assert_called_once_with(
        org_id=ORGANISATION_ID,
        invited_user_id=sample_org_invite['id'],
    )


def test_organisation_settings_platform_admin_only(
    client_request,
    mock_get_organisation,
    organisation_one
):
    client_request.get(
        '.organisation_settings',
        org_id=organisation_one['id'],
        _expected_status=403,
    )


def test_organisation_settings_for_platform_admin(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    organisation_one
):
    expected_rows = [
        'Label Value Action',
        'Name Test organisation Change organisation name',
        'Sector Central government Change sector for the organisation',
        'Crown organisation Yes Change organisation crown status',
        (
            'Data sharing and financial agreement '
            'Not signed Change data sharing and financial agreement for the organisation'
        ),
        'Request to go live notes None Change go live notes for the organisation',
        'Billing details None Change billing details for the organisation',
        'Notes None Change the notes for the organisation',
        'Default email branding GOV.UK Change default email branding for the organisation',
        'Default letter branding No branding Change default letter branding for the organisation',
        'Known email domains None Change known email domains for the organisation',
    ]

    client_request.login(platform_admin_user)
    page = client_request.get('.organisation_settings', org_id=organisation_one['id'])

    assert page.find('h1').text == 'Settings'
    rows = page.select('tr')
    assert len(rows) == len(expected_rows)
    for index, row in enumerate(expected_rows):
        assert row == " ".join(rows[index].text.split())
    mock_get_organisation.assert_called_with(organisation_one['id'])


@pytest.mark.parametrize('endpoint, expected_options, expected_selected', (
    (
        '.edit_organisation_type',
        (
            {'value': 'central', 'label': 'Central government'},
            {'value': 'local', 'label': 'Local government'},
            {'value': 'nhs_central', 'label': 'NHS – central government agency or public body'},
            {'value': 'nhs_local', 'label': 'NHS Trust or Clinical Commissioning Group'},
            {'value': 'nhs_gp', 'label': 'GP practice'},
            {'value': 'emergency_service', 'label': 'Emergency service'},
            {'value': 'school_or_college', 'label': 'School or college'},
            {'value': 'other', 'label': 'Other'},
        ),
        'central',
    ),
    (
        '.edit_organisation_crown_status',
        (
            {'value': 'crown', 'label': 'Yes'},
            {'value': 'non-crown', 'label': 'No'},
            {'value': 'unknown', 'label': 'Not sure'},
        ),
        'crown',
    ),
    (
        '.edit_organisation_agreement',
        (
            {
                'value': 'yes',
                'label': 'Yes',
                'hint': 'Users will be told their organisation has already signed the agreement'
            },
            {
                'value': 'no',
                'label': 'No',
                'hint': 'Users will be prompted to sign the agreement before they can go live'
            },
            {
                'value': 'unknown',
                'label': 'No (but we have some service-specific agreements in place)',
                'hint': 'Users will not be prompted to sign the agreement'
            },
        ),
        'no',
    ),
))
@pytest.mark.parametrize('user', (
    pytest.param(
        create_platform_admin_user(),
    ),
    pytest.param(
        create_active_user_with_permissions(),
        marks=pytest.mark.xfail
    ),
))
def test_view_organisation_settings(
    client_request,
    fake_uuid,
    organisation_one,
    mock_get_organisation,
    endpoint,
    expected_options,
    expected_selected,
    user,
):
    client_request.login(user)

    page = client_request.get(endpoint, org_id=organisation_one['id'])

    radios = page.select('input[type=radio]')

    for index, option in enumerate(expected_options):
        option_values = {
            'value': radios[index]['value'],
            'label': normalize_spaces(page.select_one('label[for={}]'.format(radios[index]['id'])).text)
        }
        if 'hint' in option:
            option_values['hint'] = normalize_spaces(
                page.select_one('label[for={}] + .govuk-hint'.format(radios[index]['id'])).text)
        assert option_values == option

    if expected_selected:
        assert page.select_one('input[checked]')['value'] == expected_selected
    else:
        assert not page.select_one('input[checked]')


@pytest.mark.parametrize('endpoint, post_data, expected_persisted', (
    (
        '.edit_organisation_type',
        {'organisation_type': 'central'},
        {'cached_service_ids': [], 'organisation_type': 'central'},
    ),
    (
        '.edit_organisation_type',
        {'organisation_type': 'local'},
        {'cached_service_ids': [], 'organisation_type': 'local'},
    ),
    (
        '.edit_organisation_type',
        {'organisation_type': 'nhs_local'},
        {'cached_service_ids': [], 'organisation_type': 'nhs_local'},
    ),
    (
        '.edit_organisation_crown_status',
        {'crown_status': 'crown'},
        {'crown': True},
    ),
    (
        '.edit_organisation_crown_status',
        {'crown_status': 'non-crown'},
        {'crown': False},
    ),
    (
        '.edit_organisation_crown_status',
        {'crown_status': 'unknown'},
        {'crown': None},
    ),
    (
        '.edit_organisation_agreement',
        {'agreement_signed': 'yes'},
        {'agreement_signed': True},
    ),
    (
        '.edit_organisation_agreement',
        {'agreement_signed': 'no'},
        {'agreement_signed': False},
    ),
    (
        '.edit_organisation_agreement',
        {'agreement_signed': 'unknown'},
        {'agreement_signed': None},
    ),
))
@pytest.mark.parametrize('user', (
    pytest.param(
        create_platform_admin_user(),
    ),
    pytest.param(
        create_active_user_with_permissions(),
        marks=pytest.mark.xfail
    ),
))
def test_update_organisation_settings(
    mocker,
    client_request,
    fake_uuid,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
    endpoint,
    post_data,
    expected_persisted,
    user,
):
    mocker.patch('app.organisations_client.get_organisation_services', return_value=[])
    client_request.login(user)

    client_request.post(
        endpoint,
        org_id=organisation_one['id'],
        _data=post_data,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.organisation_settings',
            org_id=organisation_one['id'],
            _external=True,
        ),
    )

    mock_update_organisation.assert_called_once_with(
        organisation_one['id'],
        **expected_persisted,
    )


def test_update_organisation_sector_sends_service_id_data_to_api_client(
    client_request,
    mock_get_organisation,
    organisation_one,
    mock_get_organisation_services,
    mock_update_organisation,
    platform_admin_user,
):
    client_request.login(platform_admin_user)

    client_request.post(
        'main.edit_organisation_type',
        org_id=organisation_one['id'],
        _data={'organisation_type': 'central'},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.organisation_settings',
            org_id=organisation_one['id'],
            _external=True,
        ),
    )

    mock_update_organisation.assert_called_once_with(
        organisation_one['id'],
        cached_service_ids=['12345', '67890', SERVICE_ONE_ID],
        organisation_type='central'
    )


@pytest.mark.parametrize('user', (
    pytest.param(
        create_platform_admin_user(),
    ),
    pytest.param(
        create_active_user_with_permissions(),
        marks=pytest.mark.xfail
    ),
))
def test_view_organisation_domains(
    mocker,
    client_request,
    fake_uuid,
    user,
):
    client_request.login(user)

    mocker.patch(
        'app.organisations_client.get_organisation',
        side_effect=lambda org_id: organisation_json(
            org_id,
            'Org 1',
            domains=['example.gov.uk', 'test.example.gov.uk'],
        )
    )

    page = client_request.get(
        'main.edit_organisation_domains',
        org_id=ORGANISATION_ID,
    )

    assert [textbox.get('value') for textbox in page.select('input[type=text]')] == [
        'example.gov.uk',
        'test.example.gov.uk',
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ]


@pytest.mark.parametrize('post_data, expected_persisted', (
    (
        {
            'domains-0': 'example.gov.uk',
            'domains-2': 'example.gov.uk',
            'domains-3': 'EXAMPLE.GOV.UK',
            'domains-5': 'test.gov.uk',
        },
        {
            'domains': [
                'example.gov.uk',
                'test.gov.uk',
            ]
        }
    ),
    (
        {
            'domains-0': '',
            'domains-1': '',
            'domains-2': '',
        },
        {
            'domains': []
        }
    ),
))
@pytest.mark.parametrize('user', (
    pytest.param(
        create_platform_admin_user(),
    ),
    pytest.param(
        create_active_user_with_permissions(),
        marks=pytest.mark.xfail
    ),
))
def test_update_organisation_domains(
    client_request,
    fake_uuid,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
    post_data,
    expected_persisted,
    user,
):
    client_request.login(user)

    client_request.post(
        'main.edit_organisation_domains',
        org_id=ORGANISATION_ID,
        _data=post_data,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.organisation_settings',
            org_id=organisation_one['id'],
            _external=True,
        ),
    )

    mock_update_organisation.assert_called_once_with(
        ORGANISATION_ID,
        **expected_persisted,
    )


def test_update_organisation_domains_when_domain_already_exists(
    mocker,
    client_request,
    fake_uuid,
    organisation_one,
    mock_get_organisation,
):
    user = create_platform_admin_user()
    client_request.login(user)

    mocker.patch('app.organisations_client.update_organisation', side_effect=HTTPError(
        response=mocker.Mock(
            status_code=400,
            json={'result': 'error', 'message': 'Domain already exists'}
        ),
        message="Domain already exists")
    )

    response = client_request.post(
        'main.edit_organisation_domains',
        org_id=ORGANISATION_ID,
        _data={
            'domains': [
                'example.gov.uk',
            ]
        },
        _expected_status=200,
    )

    assert response.find("div", class_="banner-dangerous").text.strip() == "This domain is already in use"


def test_update_organisation_name(
    platform_admin_client,
    organisation_one,
    mock_get_organisation,
    mock_organisation_name_is_unique
):
    response = platform_admin_client.post(
        url_for('.edit_organisation_name', org_id=organisation_one['id']),
        data={'name': 'TestNewOrgName'}
    )

    assert response.status_code == 302
    assert response.location == url_for(
        '.confirm_edit_organisation_name',
        org_id=organisation_one['id'],
        _external=True
    )
    assert mock_organisation_name_is_unique.called


@pytest.mark.parametrize('name, error_message', [
    ('', 'Cannot be empty'),
    ('a', 'at least two alphanumeric characters'),
    ('a' * 256, 'Organisation name must be 255 characters or fewer'),
])
def test_update_organisation_with_incorrect_input(
    platform_admin_client,
    organisation_one,
    mock_get_organisation,
    name,
    error_message
):
    response = platform_admin_client.post(
        url_for('.edit_organisation_name', org_id=organisation_one['id']),
        data={'name': name}
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert error_message in page.select_one('.govuk-error-message').text


def test_update_organisation_with_non_unique_name(
    platform_admin_client,
    organisation_one,
    mock_get_organisation,
    mock_organisation_name_is_not_unique
):
    response = platform_admin_client.post(
        url_for('.edit_organisation_name', org_id=organisation_one['id']),
        data={'name': 'TestNewOrgName'}
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert 'This organisation name is already in use' in page.select_one('.govuk-error-message').text

    assert mock_organisation_name_is_not_unique.called


def test_confirm_update_organisation(
    platform_admin_client,
    organisation_one,
    mock_get_organisation,
    mock_verify_password,
    mock_update_organisation,
    mocker
):
    with platform_admin_client.session_transaction() as session:
        session['organisation_name_change'] = 'newName'

    response = platform_admin_client.post(
        url_for(
            '.confirm_edit_organisation_name',
            org_id=organisation_one['id'],
            data={'password', 'validPassword'}
        )
    )

    assert response.status_code == 302
    assert response.location == url_for('.organisation_settings', org_id=organisation_one['id'], _external=True)

    mock_update_organisation.assert_called_with(
        organisation_one['id'],
        name=session['organisation_name_change']
    )


def test_confirm_update_organisation_with_incorrect_password(
    platform_admin_client,
    organisation_one,
    mock_get_organisation,
    mocker
):
    with platform_admin_client.session_transaction() as session:
        session['organisation_name_change'] = 'newName'

    mocker.patch('app.user_api_client.verify_password', return_value=False)

    response = platform_admin_client.post(
        url_for(
            '.confirm_edit_organisation_name',
            org_id=organisation_one['id']
        )
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(
        page.select_one('.govuk-error-message').text
    ) == 'Error: Invalid password'


def test_confirm_update_organisation_with_name_already_in_use(
    platform_admin_client,
    organisation_one,
    mock_get_organisation,
    mock_verify_password,
    mocker
):
    with platform_admin_client.session_transaction() as session:
        session['organisation_name_change'] = 'newName'

    mocker.patch(
        'app.organisations_client.update_organisation_name',
        side_effect=HTTPError(
            response=mocker.Mock(
                status_code=400,
                json={'result': 'error', 'message': 'Organisation name already exists'}
            ),
            message="Organisation name already exists"
        )
    )

    response = platform_admin_client.post(
        url_for(
            '.confirm_edit_organisation_name',
            org_id=organisation_one['id']
        )
    )

    assert response.status_code == 302
    assert response.location == url_for('main.edit_organisation_name', org_id=organisation_one['id'], _external=True)


def test_get_edit_organisation_go_live_notes_page(
    platform_admin_client,
    mock_get_organisation,
    organisation_one,
):
    response = platform_admin_client.get(
        url_for(
            '.edit_organisation_go_live_notes',
            org_id=organisation_one['id']
        )
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.find('textarea', id='request_to_go_live_notes')


@pytest.mark.parametrize('input_note,saved_note', [
    ('Needs permission', 'Needs permission'),
    ('  ', None)
])
def test_post_edit_organisation_go_live_notes_updates_go_live_notes(
    platform_admin_client,
    mock_get_organisation,
    mock_update_organisation,
    organisation_one,
    input_note,
    saved_note,
):
    response = platform_admin_client.post(
        url_for(
            '.edit_organisation_go_live_notes',
            org_id=organisation_one['id'],
        ),
        data={'request_to_go_live_notes': input_note}
    )

    mock_update_organisation.assert_called_once_with(
        organisation_one['id'],
        request_to_go_live_notes=saved_note
    )
    assert response.status_code == 302
    assert response.location == url_for(
        '.organisation_settings',
        org_id=organisation_one['id'],
        _external=True
    )


def test_organisation_settings_links_to_edit_organisation_notes_page(
    mocker,
    mock_get_organisation,
    organisation_one,
    platform_admin_client,
):
    response = platform_admin_client.get(url_for(
        '.organisation_settings', org_id=organisation_one['id']
    ))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert len(page.find_all(
        'a', attrs={'href': '/organisations/{}/settings/notes'.format(organisation_one['id'])}
    )) == 1


def test_view_edit_organisation_notes(
        platform_admin_client,
        organisation_one,
        mock_get_organisation,
):
    response = platform_admin_client.get(url_for('main.edit_organisation_notes', org_id=organisation_one['id']))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.select_one('h1').text == "Edit organisation notes"
    assert page.find('label', class_="form-label").text.strip() == "Notes"
    assert page.find('textarea').attrs["name"] == "notes"


def test_update_organisation_notes(
        platform_admin_client,
        organisation_one,
        mock_get_organisation,
        mock_update_organisation,
):
    response = platform_admin_client.post(
        url_for(
            'main.edit_organisation_notes',
            org_id=organisation_one['id'],
        ),
        data={'notes': "Very fluffy"}
    )
    assert response.status_code == 302
    settings_url = url_for(
        'main.organisation_settings', org_id=organisation_one['id'], _external=True)
    assert settings_url == response.location
    mock_update_organisation.assert_called_with(
        organisation_one['id'],
        cached_service_ids=None,
        notes="Very fluffy"
    )


def test_update_organisation_notes_errors_when_user_not_platform_admin(
        client_request,
        organisation_one,
        mock_get_organisation,
        mock_update_organisation,
):
    client_request.post(
        'main.edit_organisation_notes',
        org_id=organisation_one['id'],
        _data={'notes': "Very fluffy"},
        _expected_status=403,
    )


def test_update_organisation_notes_doesnt_call_api_when_notes_dont_change(
        platform_admin_client,
        organisation_one,
        mock_update_organisation,
        mocker
):
    mocker.patch('app.organisations_client.get_organisation', return_value=organisation_json(
        id_=organisation_one['id'],
        name="Test Org",
        notes="Very fluffy"
    ))
    response = platform_admin_client.post(
        url_for(
            'main.edit_organisation_notes',
            org_id=organisation_one['id'],
        ),
        data={'notes': "Very fluffy"}
    )
    assert response.status_code == 302
    settings_url = url_for(
        'main.organisation_settings', org_id=organisation_one['id'], _external=True)
    assert response.location == settings_url
    assert not mock_update_organisation.called


def test_organisation_settings_links_to_edit_organisation_billing_details_page(
    mocker,
    mock_get_organisation,
    organisation_one,
    platform_admin_client,
):
    response = platform_admin_client.get(url_for(
        '.organisation_settings', org_id=organisation_one['id']
    ))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert len(page.find_all(
        'a', attrs={'href': '/organisations/{}/settings/edit-billing-details'.format(organisation_one['id'])}
    )) == 1


def test_view_edit_organisation_billing_details(
        platform_admin_client,
        organisation_one,
        mock_get_organisation,
):
    response = platform_admin_client.get(
        url_for('main.edit_organisation_billing_details', org_id=organisation_one['id'])
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.select_one('h1').text == "Edit organisation billing details"
    labels = page.find_all('label', class_="form-label")
    labels_list = [
        'Contact email addresses',
        'Contact names',
        'Reference',
        'Purchase order number',
        'Notes'
    ]
    for label in labels:
        assert label.text.strip() in labels_list
    textbox_names = page.find_all('input', class_='govuk-input govuk-!-width-full')
    names_list = [
        'billing_contact_email_addresses',
        'billing_contact_names',
        'billing_reference',
        'purchase_order_number',
    ]

    for name in textbox_names:
        assert name.attrs["name"] in names_list

    assert page.find('textarea').attrs["name"] == "notes"


def test_update_organisation_billing_details(
        platform_admin_client,
        organisation_one,
        mock_get_organisation,
        mock_update_organisation,
):
    response = platform_admin_client.post(
        url_for(
            'main.edit_organisation_billing_details',
            org_id=organisation_one['id'],
        ),
        data={
            'billing_contact_email_addresses': 'accounts@fluff.gov.uk',
            'billing_contact_names': 'Flannellette von Fluff',
            'billing_reference': '',
            'purchase_order_number': 'PO1234',
            'notes': 'very fluffy, give extra allowance'
        }
    )
    assert response.status_code == 302
    settings_url = url_for(
        'main.organisation_settings', org_id=organisation_one['id'], _external=True)
    assert settings_url == response.location
    mock_update_organisation.assert_called_with(
        organisation_one['id'],
        cached_service_ids=None,
        billing_contact_email_addresses='accounts@fluff.gov.uk',
        billing_contact_names='Flannellette von Fluff',
        billing_reference='',
        purchase_order_number='PO1234',
        notes='very fluffy, give extra allowance'
    )


def test_update_organisation_billing_details_errors_when_user_not_platform_admin(
        client_request,
        organisation_one,
        mock_get_organisation,
        mock_update_organisation,
):
    client_request.post(
        'main.edit_organisation_billing_details',
        org_id=organisation_one['id'],
        _data={'notes': "Very fluffy"},
        _expected_status=403,
    )
