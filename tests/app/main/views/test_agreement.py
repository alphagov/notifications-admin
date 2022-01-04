from functools import partial
from io import BytesIO
from unittest.mock import call

import pytest
from flask import url_for
from freezegun import freeze_time

from tests import organisation_json
from tests.conftest import ORGANISATION_ID, SERVICE_ONE_ID, normalize_spaces


class MockS3Object():

    def __init__(self, data=None):
        self.data = data or b''

    def get(self):
        return {'Body': BytesIO(self.data)}


@pytest.mark.parametrize('agreement_signed, crown, expected_back_link, expected_other_links', [
    (
        True, True,
        partial(url_for, 'main.request_to_go_live', service_id=SERVICE_ONE_ID),
        [
            (
                ['govuk-link', 'govuk-link--no-visited-state'],
                partial(url_for, 'main.service_download_agreement', service_id=SERVICE_ONE_ID),
            ),
        ]
    ),
    (
        False, False,
        partial(url_for, 'main.request_to_go_live', service_id=SERVICE_ONE_ID),
        [
            (
                ['govuk-link', 'govuk-link--no-visited-state'],
                partial(url_for, 'main.service_download_agreement', service_id=SERVICE_ONE_ID),
            ),
            (
                ['govuk-button'],
                partial(url_for, 'main.service_accept_agreement', service_id=SERVICE_ONE_ID),
            ),
        ]
    ),
    (
        False, True,
        partial(url_for, 'main.request_to_go_live', service_id=SERVICE_ONE_ID),
        [
            (
                ['govuk-link', 'govuk-link--no-visited-state'],
                partial(url_for, 'main.service_download_agreement', service_id=SERVICE_ONE_ID),
            ),
            (
                ['govuk-button'],
                partial(url_for, 'main.service_accept_agreement', service_id=SERVICE_ONE_ID),
            ),
        ]
    ),
    (
        None, None,
        partial(url_for, 'main.request_to_go_live', service_id=SERVICE_ONE_ID),
        [
            (
                ['govuk-link', 'govuk-link--no-visited-state'],
                partial(url_for, 'main.support'),
            ),
        ]
    ),
])
def test_show_agreement_page(
    client_request,
    mocker,
    fake_uuid,
    mock_get_service_organisation,
    mock_has_jobs,
    agreement_signed,
    crown,
    expected_back_link,
    expected_other_links,
):
    org = organisation_json(
        crown=crown,
        agreement_signed=agreement_signed
    )
    mocker.patch('app.organisations_client.get_organisation', return_value=org)

    page = client_request.get('main.service_agreement', service_id=SERVICE_ONE_ID)

    back_link = page.select_one('.govuk-back-link')
    assert back_link['href'] == expected_back_link()

    links = page.select('main .govuk-grid-column-five-sixths a')
    assert len(links) == len(expected_other_links)
    for index, link in enumerate(links):
        classes, url = expected_other_links[index]
        assert link.get('class', []) == classes
        assert link['href'] == url()


@pytest.mark.parametrize('org_type, expected_endpoint', (
    ('nhs_gp', 'main.add_organisation_from_gp_service'),
    ('nhs_local', 'main.add_organisation_from_nhs_local_service'),
))
def test_unknown_gps_and_trusts_are_redirected(
    client_request,
    mocker,
    fake_uuid,
    mock_has_jobs,
    service_one,
    org_type,
    expected_endpoint,
):
    service_one['organisation_id'] = None
    service_one['organisation_type'] = org_type
    client_request.get(
        'main.service_agreement',
        service_id=SERVICE_ONE_ID,
        _expected_status=302,
        _expected_redirect=url_for(
            expected_endpoint,
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    )


@pytest.mark.parametrize('crown, expected_status, expected_file_fetched, expected_file_served', (
    (
        True, 200, 'crown.pdf',
        'GOV.UK Notify data sharing and financial agreement.pdf',
    ),
    (
        False, 200, 'non-crown.pdf',
        'GOV.UK Notify data sharing and financial agreement (non-crown).pdf',
    ),
    (
        None, 404, None,
        None,
    ),
))
def test_download_service_agreement(
    client_request,
    mocker,
    mock_get_service_organisation,
    crown,
    expected_status,
    expected_file_fetched,
    expected_file_served,
):
    mocker.patch(
        'app.models.organisation.organisations_client.get_organisation',
        return_value=organisation_json(
            crown=crown
        )
    )
    mock_get_s3_object = mocker.patch(
        'app.s3_client.s3_mou_client.get_s3_object',
        return_value=MockS3Object(b'foo')
    )

    response = client_request.get_response(
        'main.service_download_agreement',
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_status,
    )

    if expected_file_served:
        assert response.get_data() == b'foo'
        assert response.headers['Content-Type'] == 'application/pdf'
        assert response.headers['Content-Disposition'] == (
            'attachment; filename="{}"'.format(expected_file_served)
        )
        mock_get_s3_object.assert_called_once_with('test-mou', expected_file_fetched)
    else:
        assert not expected_file_fetched
        assert mock_get_s3_object.called is False


def test_show_accept_agreement_page(
    client_request,
    mocker,
    mock_get_service_organisation,
    mock_get_organisation,
):
    page = client_request.get('main.service_accept_agreement', service_id=SERVICE_ONE_ID)

    assert [
        (input['type'], input['name'], input.get('id')) for input in page.select('input')
    ] == [
        ('radio', 'who', 'who-0'),
        ('radio', 'who', 'who-1'),
        ('text', 'on_behalf_of_name', 'on_behalf_of_name'),
        ('email', 'on_behalf_of_email', 'on_behalf_of_email'),
        ('text', 'version', 'version'),
        ('hidden', 'csrf_token', None),
    ]

    assert normalize_spaces(page.select_one('label[for=version]').text) == (
        'Which version of the agreement do you want to accept?'
    )

    assert normalize_spaces(page.select_one('#version-hint').text) == (
        'The version number is on the front page, for example ‘3.6’'
    )
    assert page.select_one('input[name=version]').get('value') is None

    assert normalize_spaces(page.select_one('#who legend').text) == (
        'Who are you accepting the agreement for?'
    )
    assert normalize_spaces(page.select_one('label[for=who-0]').text) == (
        'Yourself'
    )
    assert page.select('input[name=who]')[0]['value'] == 'me'
    assert 'checked' not in page.select('input[name=who]')[0]
    assert 'data-target' not in page.select('.multiple-choice')[0]
    assert normalize_spaces(page.select_one('label[for=who-1]').text) == (
        'Someone else'
    )
    assert page.select('input[name=who]')[1]['value'] == 'someone-else'
    assert 'checked' not in page.select('input[name=who]')[1]
    assert page.select('.multiple-choice')[1]['data-target'] == 'on-behalf-of'
    assert [
        field['name']
        for field in page.select('#on-behalf-of.conditional-radios-panel input')
    ] == [
        'on_behalf_of_name', 'on_behalf_of_email'
    ]

    assert normalize_spaces(page.select_one('label[for=on_behalf_of_name]').text) == (
        'What’s their name?'
    )
    assert page.select_one('input[name=on_behalf_of_name]').get('value') is None

    assert normalize_spaces(page.select_one('label[for=on_behalf_of_email]').text) == (
        'What’s their email address?'
    )
    assert page.select_one('input[name=on_behalf_of_email]').get('value') is None


def test_accept_agreement_page_populates(
    client_request,
    mocker,
    mock_get_service_organisation,
):
    mocker.patch(
        'app.models.organisation.organisations_client.get_organisation',
        return_value=organisation_json(
            agreement_signed_version='1.2',
            agreement_signed_on_behalf_of_name='Firstname Lastname',
            agreement_signed_on_behalf_of_email_address='test@example.com',
        )
    )

    page = client_request.get('main.service_accept_agreement', service_id=SERVICE_ONE_ID)

    assert [
        (field['name'], field['value']) for field in page.select('input[type=text], input[type=email]')
    ] == [
        ('on_behalf_of_name', 'Firstname Lastname'),
        ('on_behalf_of_email', 'test@example.com'),
        ('version', '1.2'),
    ]
    assert 'checked' not in page.select('input[name=who]')[0]
    assert page.select('input[name=who]')[1]['checked'] == ''


@pytest.mark.parametrize('data, expected_errors', (
    (
        {
            'version': '',
            'on_behalf_of_name': '',
            'on_behalf_of_email': '',
        },
        [
            'Select an option',
            'Error: Must be a number',
        ],
    ),
    (
        {
            'version': 'one point two',
            'who': 'me',
            'on_behalf_of_name': '',
            'on_behalf_of_email': '',
        },
        [
            'Error: Must be a number',
        ],
    ),
    (
        {
            'version': '1.2',
            'who': 'someone-else',
            'on_behalf_of_name': '',
            'on_behalf_of_email': '',
        },
        [
            'Error: Cannot be empty',
            'Error: Cannot be empty',
        ],
    ),
    (
        {
            'version': '1.2',
            'who': 'someone-else',
            'on_behalf_of_name': 'Firstname Lastname',
            'on_behalf_of_email': '',
        },
        [
            'Error: Cannot be empty',
        ],
    ),
    (
        {
            'version': '1.2',
            'who': 'someone-else',
            'on_behalf_of_name': '',
            'on_behalf_of_email': 'test@example.com',
        },
        [
            'Error: Cannot be empty',
        ],
    ),

))
def test_accept_agreement_page_validates(
    mocker,
    client_request,
    mock_get_service_organisation,
    data,
    expected_errors,
):
    page = client_request.post(
        'main.service_accept_agreement',
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=200,
    )
    assert [
        error.text.strip() for error in page.select('.govuk-error-message, .error-message')
    ] == expected_errors


@pytest.mark.parametrize('data, expected_persisted', (
    (
        {
            'version': '1.2',
            'who': 'someone-else',
            'on_behalf_of_name': 'Firstname Lastname',
            'on_behalf_of_email': 'test@example.com',
        },
        call(
            ORGANISATION_ID,
            agreement_signed_version=1.2,
            agreement_signed_on_behalf_of_name='Firstname Lastname',
            agreement_signed_on_behalf_of_email_address='test@example.com',
            cached_service_ids=None,
        )
    ),
    (
        {
            'version': '1.2',
            'who': 'me',
            'on_behalf_of_name': 'Firstname Lastname',
            'on_behalf_of_email': 'test@example.com',
        },
        call(
            ORGANISATION_ID,
            agreement_signed_version=1.2,
            agreement_signed_on_behalf_of_name='',
            agreement_signed_on_behalf_of_email_address='',
            cached_service_ids=None,
        )
    ),
    (
        {
            'version': '1.2',
            'who': 'me',
            'on_behalf_of_name': '',
            'on_behalf_of_email': '',
        },
        call(
            ORGANISATION_ID,
            agreement_signed_version=1.2,
            agreement_signed_on_behalf_of_name='',
            agreement_signed_on_behalf_of_email_address='',
            cached_service_ids=None,
        )
    ),
))
def test_accept_agreement_page_persists(
    mocker,
    client_request,
    mock_get_service_organisation,
    mock_update_organisation,
    data,
    expected_persisted,
):
    client_request.post(
        'main.service_accept_agreement',
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_confirm_agreement',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    )
    assert mock_update_organisation.call_args_list == [expected_persisted]


@pytest.mark.parametrize('name, email, expected_paragraph', (
    (None, None, (
        'I confirm that I have the legal authority to accept the '
        'GOV.UK Notify data sharing and financial agreement (version '
        '1.2) and that Test Organisation will be bound by it.'
    )),
    ('Firstname Lastname', 'test@example.com', (
        'I confirm that I have the legal authority to accept the '
        'GOV.UK Notify data sharing and financial agreement (version '
        '1.2) on behalf of Firstname Lastname (test@example.com) and '
        'that Test Organisation will be bound by it.'
    )),
))
def test_show_confirm_agreement_page(
    client_request,
    mocker,
    mock_get_service_organisation,
    name,
    email,
    expected_paragraph,
):
    mocker.patch(
        'app.models.organisation.organisations_client.get_organisation',
        return_value=organisation_json(
            agreement_signed_version='1.2',
            agreement_signed_on_behalf_of_name=name,
            agreement_signed_on_behalf_of_email_address=email,
        )
    )
    page = client_request.get('main.service_confirm_agreement', service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select_one('main p').text) == expected_paragraph


@pytest.mark.parametrize('http_method', ('get', 'post'))
def test_confirm_agreement_page_403s_if_previous_step_not_taken(
    client_request,
    mock_get_organisation,
    http_method,
):
    getattr(client_request, http_method)(
        'main.service_confirm_agreement',
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


@freeze_time("2012-01-01 01:01")
def test_confirm_agreement_page_persists(
    client_request,
    mocker,
    mock_get_service_organisation,
    mock_update_organisation,
    fake_uuid,
):
    mocker.patch(
        'app.models.organisation.organisations_client.get_organisation',
        return_value=organisation_json(agreement_signed_version='1.2')
    )
    client_request.post(
        'main.service_confirm_agreement',
        service_id=SERVICE_ONE_ID,
        _expected_redirect=url_for(
            'main.request_to_go_live',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    )
    mock_update_organisation.assert_called_once_with(
        '1234',
        agreement_signed=True,
        agreement_signed_at='2012-01-01 01:01:00',
        agreement_signed_by_id=fake_uuid,
        cached_service_ids=None,
    )


@pytest.mark.parametrize('endpoint', (
    'main.public_agreement',
    'main.public_download_agreement',
))
@pytest.mark.parametrize('variant, expected_status', (
    ('crown', 200),
    ('non-crown', 200),
    ('foo', 404),
))
def test_show_public_agreement_page(
    client_request,
    mocker,
    endpoint,
    variant,
    expected_status,
):
    mocker.patch(
        'app.s3_client.s3_mou_client.get_s3_object',
        return_value=MockS3Object()
    )
    client_request.logout()
    client_request.get_response(
        endpoint,
        variant=variant,
        _expected_status=expected_status,
    )
