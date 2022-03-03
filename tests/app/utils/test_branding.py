import pytest

from app.models.service import Service
from app.utils.branding import get_available_choices
from tests import organisation_json


@pytest.mark.parametrize('branding_type', ['email', 'letter'])
@pytest.mark.parametrize('org_type, existing_branding, expected_options', [
    ('central', None, []),
    ('local', None, []),
    ('nhs_central', None, [('nhs', 'NHS')]),
    ('nhs_local', None, [('nhs', 'NHS')]),
    ('nhs_gp', None, [('nhs', 'NHS')]),
    ('emergency_service', None, []),
    ('other', None, []),
])
def test_get_available_choices_no_org(
    service_one,
    branding_type,
    org_type,
    existing_branding,
    expected_options,
):
    service_one['organisation_type'] = org_type
    service = Service(service_one)

    options = get_available_choices(service, branding_type=branding_type)
    assert list(options) == expected_options


@pytest.mark.parametrize('branding_type', ['email', 'letter'])
@pytest.mark.parametrize('org_type, existing_branding, expected_options', [
    ('local', None, [('organisation', 'Test Organisation')]),
    ('nhs_central', None, [('nhs', 'NHS')]),
    ('nhs_local', None, [('nhs', 'NHS')]),
    ('nhs_gp', None, [('nhs', 'NHS')]),
    ('emergency_service', None, [('organisation', 'Test Organisation')]),
    ('other', None, [('organisation', 'Test Organisation')]),
])
def test_get_available_choices_with_org(
    mocker,
    service_one,
    branding_type,
    org_type,
    existing_branding,
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


@pytest.mark.parametrize('branding_type, expected_options', [
    ('email', [
        ('govuk_and_org', 'GOV.UK and Test Organisation'),
        ('organisation', 'Test Organisation'),
    ]),
    ('letter', [
        ('organisation', 'Test Organisation'),
    ])
])
def test_get_available_choices_with_central_org(
    mocker,
    service_one,
    branding_type,
    expected_options,
    mock_get_service_organisation,
):
    service = Service(service_one)

    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(organisation_type='central'),
    )

    options = get_available_choices(service, branding_type=branding_type)
    assert list(options) == expected_options
