from unittest.mock import PropertyMock

import pytest

from app.models.service import Service
from app.utils.branding import get_email_choices, get_letter_choices
from tests import organisation_json


@pytest.mark.parametrize('function', [get_email_choices, get_letter_choices])
@pytest.mark.parametrize('org_type, expected_options', [
    ('central', []),
    ('local', []),
    ('nhs_central', [('nhs', 'NHS')]),
])
def test_get_choices_service_not_assigned_to_org(
    service_one,
    function,
    org_type,
    expected_options,
):
    service_one['organisation_type'] = org_type
    service = Service(service_one)

    options = function(service)
    assert list(options) == expected_options


@pytest.mark.parametrize('org_type, expected_options', [
    ('central', [
        ('govuk_and_org', 'GOV.UK and Test Organisation'),
        ('organisation', 'Test Organisation'),
    ]),
    ('local', [('organisation', 'Test Organisation')]),
    ('nhs_central', [('nhs', 'NHS')]),
])
def test_get_email_choices_service_assigned_to_org(
    mocker,
    service_one,
    org_type,
    expected_options,
    mock_get_service_organisation,
):
    service = Service(service_one)

    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(organisation_type=org_type)
    )

    options = get_email_choices(service)
    assert list(options) == expected_options


def test_get_email_choices_central_org_includes_govuk(
    mocker,
    service_one,
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
        return_value='some-random-branding',
    )

    assert list(get_email_choices(service)) == [
        ('govuk', 'GOV.UK'),  # central orgs can switch back to GOV.UK
        ('govuk_and_org', 'GOV.UK and Test Organisation'),
        ('organisation', 'Test Organisation'),
    ]


@pytest.mark.parametrize('org_type, expected_options', [
    ('central', [('organisation', 'Test Organisation')]),
    ('local', [('organisation', 'Test Organisation')]),
    ('nhs_central', [('nhs', 'NHS')]),
])
def test_get_letter_choices_service_assigned_to_org(
    mocker,
    service_one,
    org_type,
    expected_options,
    mock_get_service_organisation,
):
    service = Service(service_one)

    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(organisation_type=org_type)
    )

    options = get_letter_choices(service)
    assert list(options) == expected_options


def test_get_letter_choices_branding_set(
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
        return_value='some-random-branding',
    )

    options = get_letter_choices(service)
    assert list(options) == [
        ('organisation', 'Test Organisation'),
    ]
