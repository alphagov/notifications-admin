from functools import partial
from io import BytesIO
from unittest.mock import call

import pytest
from flask import url_for
from freezegun import freeze_time

from tests import organisation_json
from tests.conftest import (
    SERVICE_ONE_ID,
    mock_get_organisation_by_domain,
    mock_get_service_organisation,
    normalize_spaces,
)


class _MockS3Object():

    def __init__(self, data=None):
        self.data = data or b''

    def get(self):
        return {'Body': BytesIO(self.data)}


@pytest.mark.parametrize('endpoint, extra_args, organisation_mock, link_selector, expected_back_links', [
    (
        'main.agreement',
        {},
        mock_get_organisation_by_domain,
        'main .column-two-thirds a',
        []
    ),
    (
        'main.service_agreement',
        {'service_id': SERVICE_ONE_ID},
        mock_get_service_organisation,
        'main .column-five-sixths a',
        [
            partial(url_for, 'main.request_to_go_live', service_id=SERVICE_ONE_ID)
        ]
    ),
])
@pytest.mark.parametrize('agreement_signed, crown, expected_links', [
    (
        True, True,
        [
            partial(url_for, 'main.download_agreement'),
        ]
    ),
    (
        False, False,
        [
            partial(url_for, 'main.download_agreement'),
            partial(url_for, 'main.service_accept_agreement', service_id=SERVICE_ONE_ID),
        ]
    ),
    (
        False, True,
        [
            partial(url_for, 'main.download_agreement'),
            partial(url_for, 'main.service_accept_agreement', service_id=SERVICE_ONE_ID),
        ]
    ),
    (
        None, None,
        [
            partial(url_for, 'main.public_download_agreement', variant='crown'),
            partial(url_for, 'main.public_download_agreement', variant='non-crown'),
            partial(url_for, 'main.support'),
            lambda: 'mailto:notify-support@digital.cabinet-office.gov.uk',
        ]
    ),
])
def test_show_agreement_page(
    client_request,
    mocker,
    fake_uuid,
    mock_has_jobs,
    mock_get_service_organisation,
    agreement_signed,
    crown,
    expected_links,
    endpoint,
    extra_args,
    organisation_mock,
    link_selector,
    expected_back_links,
):
    organisation_mock(
        mocker,
        crown=crown,
        agreement_signed=agreement_signed,
    )
    expected_links = expected_back_links + expected_links
    page = client_request.get(endpoint, **extra_args)
    links = page.select(link_selector)
    assert len(links) == len(expected_links)
    for index, link in enumerate(links):
        assert link['href'] == expected_links[index]()


def test_show_accept_agreement_page(
    client_request,
    mocker,
    mock_get_service_organisation,
):
    page = client_request.get('main.service_accept_agreement', service_id=SERVICE_ONE_ID)

    assert [
        (input['type'], input['name'], input.get('id')) for input in page.select('input')
    ] == [
        ('text', 'version', 'version'),
        ('radio', 'who', 'who-0'),
        ('radio', 'who', 'who-1'),
        ('text', 'on_behalf_of_name', 'on_behalf_of_name'),
        ('email', 'on_behalf_of_email', 'on_behalf_of_email'),
        ('hidden', 'csrf_token', None),
    ]

    assert normalize_spaces(page.select_one('label[for=version]').text) == (
        'Which version of the agreement are you accepting? '
        'The version number is on the front page, for example ‘3.6’'
    )
    assert page.select_one('input[name=version]')['value'] == ''

    assert normalize_spaces(page.select_one('#who legend').text) == (
        'Who is accepting the agreement?'
    )
    assert normalize_spaces(page.select_one('label[for=who-0]').text) == (
        'I’m accepting the agreement'
    )
    assert page.select('input[name=who]')[0]['value'] == 'me'
    assert 'checked' not in page.select('input[name=who]')[0]
    assert normalize_spaces(page.select_one('label[for=who-1]').text) == (
        'I’m accepting the agreement on behalf of someone else'
    )
    assert page.select('input[name=who]')[1]['value'] == 'someone-else'
    assert 'checked' not in page.select('input[name=who]')[1]

    assert normalize_spaces(page.select_one('label[for=on_behalf_of_name]').text) == (
        'Who are you accepting the agreement on behalf of?'
    )
    assert page.select_one('input[name=on_behalf_of_name]')['value'] == ''

    assert normalize_spaces(page.select_one('label[for=on_behalf_of_email]').text) == (
        'What’s their email address?'
    )
    assert page.select_one('input[name=on_behalf_of_email]')['value'] == ''


def test_accept_agreement_page_populates(
    client_request,
    mocker,
    mock_get_service_organisation,
):
    mocker.patch(
        'app.models.organisation.organisations_client.get_service_organisation',
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
        ('version', '1.2'),
        ('on_behalf_of_name', 'Firstname Lastname'),
        ('on_behalf_of_email', 'test@example.com'),
    ]
    assert 'checked' not in page.select('input[name=who]')[0]
    assert page.select('input[name=who]')[1]['checked'] == ''


@pytest.mark.parametrize('data, expected_errors', (
    (
        {
            'version': '',
            'who': '',
            'on_behalf_of_name': '',
            'on_behalf_of_email': '',
        },
        [
            'Must be a number',
            'This field is required.',
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
            'Must be a number',
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
            'Can’t be empty',
            'Can’t be empty',
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
            'Can’t be empty',
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
            'Can’t be empty',
        ],
    ),

))
def test_accept_agreement_page_validates(
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
        error.text.strip() for error in page.select('.error-message')
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
            '7aa5d4e9-4385-4488-a489-07812ba13383',
            agreement_signed_version=1.2,
            agreement_signed_on_behalf_of_name='Firstname Lastname',
            agreement_signed_on_behalf_of_email_address='test@example.com',
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
            '7aa5d4e9-4385-4488-a489-07812ba13383',
            agreement_signed_version=1.2,
            agreement_signed_on_behalf_of_name='',
            agreement_signed_on_behalf_of_email_address='',
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
            '7aa5d4e9-4385-4488-a489-07812ba13383',
            agreement_signed_version=1.2,
            agreement_signed_on_behalf_of_name='',
            agreement_signed_on_behalf_of_email_address='',
        )
    ),
))
def test_accept_agreement_page_persists(
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
    name,
    email,
    expected_paragraph,
):
    mocker.patch(
        'app.models.organisation.organisations_client.get_service_organisation',
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
    mock_get_service_organisation,
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
    mock_update_organisation,
    fake_uuid,
):
    mocker.patch(
        'app.models.organisation.organisations_client.get_service_organisation',
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
    )


@pytest.mark.parametrize('crown, expected_file_fetched, expected_file_served', [
    (
        True,
        'crown.pdf',
        'GOV.UK Notify data sharing and financial agreement.pdf',
    ),
    (
        False,
        'non-crown.pdf',
        'GOV.UK Notify data sharing and financial agreement (non-crown).pdf',
    ),
])
def test_downloading_agreement(
    logged_in_client,
    mocker,
    fake_uuid,
    crown,
    expected_file_fetched,
    expected_file_served,
):
    mock_get_s3_object = mocker.patch(
        'app.s3_client.s3_mou_client.get_s3_object',
        return_value=_MockS3Object(b'foo')
    )
    mock_get_organisation_by_domain(
        mocker,
        crown=crown,
    )
    response = logged_in_client.get(url_for('main.download_agreement'))
    assert response.status_code == 200
    assert response.get_data() == b'foo'
    assert response.headers['Content-Type'] == 'application/pdf'
    assert response.headers['Content-Disposition'] == (
        'attachment; filename="{}"'.format(expected_file_served)
    )
    mock_get_s3_object.assert_called_once_with('test-mou', expected_file_fetched)


def test_agreement_cant_be_downloaded_unknown_crown_status(
    logged_in_client,
    mocker,
    fake_uuid,
):
    mock_get_s3_object = mocker.patch(
        'app.s3_client.s3_mou_client.get_s3_object',
        return_value=_MockS3Object()
    )
    mock_get_organisation_by_domain(
        mocker,
        crown=None,
    )
    response = logged_in_client.get(url_for('main.download_agreement'))
    assert response.status_code == 404
    assert mock_get_s3_object.call_args_list == []


def test_agreement_requires_login(
    client,
    mocker,
):
    mock_get_s3_object = mocker.patch(
        'app.s3_client.s3_mou_client.get_s3_object',
        return_value=_MockS3Object()
    )
    response = client.get(url_for('main.download_agreement'))
    assert response.status_code == 302
    assert response.location == 'http://localhost/sign-in?next=%2Fagreement.pdf'
    assert mock_get_s3_object.call_args_list == []


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
    client,
    mocker,
    endpoint,
    variant,
    expected_status,
):
    mocker.patch(
        'app.s3_client.s3_mou_client.get_s3_object',
        return_value=_MockS3Object()
    )
    response = client.get(url_for(
        endpoint,
        variant=variant,
    ))
    assert response.status_code == expected_status
