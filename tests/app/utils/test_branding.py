from unittest.mock import PropertyMock

import pytest

from app.models.service import Service
from app.utils.branding import get_available_choices
from tests import organisation_json


@pytest.mark.parametrize('branding_type', ['email', 'letter'])
@pytest.mark.parametrize('org_type, expected_options', [
    ('central', []),
    ('local', []),
    ('nhs_central', [('nhs', 'NHS')]),
    ('nhs_local', [('nhs', 'NHS')]),
    ('nhs_gp', [('nhs', 'NHS')]),
    ('emergency_service', []),
    ('other', []),
])
def test_get_available_choices_service_not_assigned_to_org(
    service_one,
    branding_type,
    org_type,
    expected_options,
):
    service_one['organisation_type'] = org_type
    service = Service(service_one)

    options = get_available_choices(service, branding_type=branding_type)
    assert list(options) == expected_options


@pytest.mark.parametrize('branding_type', ['email', 'letter'])
@pytest.mark.parametrize('org_type, expected_options', [
    ('local', [('organisation', 'Test Organisation')]),
    ('nhs_central', [('nhs', 'NHS')]),
    ('nhs_local', [('nhs', 'NHS')]),
    ('nhs_gp', [('nhs', 'NHS')]),
    ('emergency_service', [('organisation', 'Test Organisation')]),
    ('other', [('organisation', 'Test Organisation')]),
])
def test_get_available_choices_service_assigned_to_org(
    mocker,
    service_one,
    branding_type,
    org_type,
    expected_options,
    mock_get_service_organisation,
):
    service = Service(service_one)

    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(organisation_type=org_type)
    )

    options = get_available_choices(service, branding_type=branding_type)
    assert list(options) == expected_options


@pytest.mark.parametrize('service_branding, expected_options', [
    (None, [
        ('govuk_and_org', 'GOV.UK and Test Organisation'),
        ('organisation', 'Test Organisation'),
    ]),
    ('1234-abcd', [
        ('govuk', 'GOV.UK'),
        ('govuk_and_org', 'GOV.UK and Test Organisation'),
        ('organisation', 'Test Organisation'),
    ])
])
def test_get_available_choices_email_branding_central_org(
    mocker,
    service_one,
    service_branding,
    expected_options,
    mock_get_service_organisation,
    mock_get_email_branding,
):
    service = Service(service_one)

    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(organisation_type='central'),
    )
    mocker.patch(
        'app.models.service.Service.email_branding_id',
        new_callable=PropertyMock,
        return_value=service_branding,
    )

    options = get_available_choices(service, branding_type='email')
    assert list(options) == expected_options


def test_get_available_choices_letter_branding_set(
    mocker,
    service_one,
    mock_get_service_organisation,
    mock_get_letter_branding_by_id,
):
    service = Service(service_one)

    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json()
    )
    mocker.patch(
        'app.models.service.Service.letter_branding_id',
        new_callable=PropertyMock,
        return_value='1234-abcd',
    )

    options = get_available_choices(service, branding_type='letter')
    assert list(options) == [
        ('organisation', 'Test Organisation'),
    ]
