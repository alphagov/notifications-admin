from unittest.mock import PropertyMock

import pytest

from app.models.branding import EmailBranding, LetterBranding
from app.models.service import Service
from app.utils.branding import get_email_choices, get_letter_choices
from tests import organisation_json
from tests.conftest import create_email_branding


@pytest.mark.parametrize(
    "function, org_type, expected_options",
    [
        (get_email_choices, "central", []),
        (get_letter_choices, "central", []),
        (get_email_choices, "local", []),
        (get_letter_choices, "local", []),
        (get_email_choices, "nhs_central", [(EmailBranding.NHS_ID, "NHS")]),
        (get_letter_choices, "nhs_central", [(LetterBranding.NHS_ID, "NHS")]),
    ],
)
def test_get_choices_service_not_assigned_to_org(
    service_one,
    function,
    mock_get_empty_email_branding_pool,
    org_type,
    expected_options,
):
    service_one["organisation_type"] = org_type
    service = Service(service_one)

    options = function(service)
    assert list(options) == expected_options


@pytest.mark.parametrize(
    "org_type, branding_id, expected_options",
    [
        (
            "central",
            None,
            [
                ("govuk_and_org", "GOV.UK and Test Organisation"),
                ("organisation", "Test Organisation"),
            ],
        ),
        (
            "central",
            "some-branding-id",
            [
                ("govuk", "GOV.UK"),  # central orgs can switch back to GOV.UK
                ("govuk_and_org", "GOV.UK and Test Organisation"),
                ("organisation", "Test Organisation"),
            ],
        ),
        ("local", None, [("organisation", "Test Organisation")]),
        ("local", "some-branding-id", [("organisation", "Test Organisation")]),
        (
            "nhs_central",
            None,
            [
                (EmailBranding.NHS_ID, "NHS"),
                ("organisation", "Test Organisation"),
            ],
        ),
        (
            "nhs_central",
            EmailBranding.NHS_ID,
            [
                # don't show NHS if it's the current branding
                ("organisation", "Test Organisation"),
            ],
        ),
    ],
)
def test_get_email_choices_service_assigned_to_org(
    mocker,
    service_one,
    org_type,
    branding_id,
    expected_options,
    mock_get_empty_email_branding_pool,
    mock_get_service_organisation,
    mock_get_email_branding,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(organisation_type=org_type)
    )
    mocker.patch("app.models.service.Service.email_branding_id", new_callable=PropertyMock, return_value=branding_id)

    options = get_email_choices(service)
    assert list(options) == expected_options


@pytest.mark.parametrize(
    "org_type, expected_options",
    [
        (
            "central",
            [
                ("govuk", "GOV.UK"),
                ("govuk_and_org", "GOV.UK and Test Organisation"),
                ("organisation", "Test Organisation"),
            ],
        ),
        (
            "local",
            [
                ("organisation", "Test Organisation"),
            ],
        ),
    ],
)
def test_get_email_choices_org_has_default_branding(
    mocker,
    service_one,
    org_type,
    expected_options,
    mock_get_empty_email_branding_pool,
    mock_get_service_organisation,
    mock_get_email_branding,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(organisation_type=org_type),
    )
    mocker.patch("app.models.service.Service.email_branding_id")

    options = get_email_choices(service)
    assert list(options) == expected_options


@pytest.mark.parametrize(
    "branding_name, expected_options",
    [
        (
            "GOV.UK and something else",
            [
                ("govuk", "GOV.UK"),
                ("govuk_and_org", "GOV.UK and Test Organisation"),
                ("organisation", "Test Organisation"),
            ],
        ),
        (
            "GOv.Uk and test OrganisatioN",
            [
                ("govuk", "GOV.UK"),
                ("organisation", "Test Organisation"),
            ],
        ),
    ],
)
def test_get_email_choices_branding_name_in_use(
    mocker,
    service_one,
    branding_name,
    expected_options,
    mock_get_empty_email_branding_pool,
    mock_get_service_organisation,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(organisation_type="central")
    )
    mocker.patch(
        "app.models.service.Service.email_branding_id",
        new_callable=PropertyMock,
        return_value="some-branding-id",
    )
    mocker.patch(
        "app.email_branding_client.get_email_branding",
        return_value=create_email_branding("_id", {"name": branding_name}),
    )

    options = get_email_choices(service)
    # don't show option if its name is similar to current branding
    assert list(options) == expected_options


@pytest.mark.parametrize(
    "branding_pool, expected_options",
    (
        (
            [
                {
                    "logo": "example_1.png",
                    "name": "Email branding name 1",
                    "text": "Email branding text 1",
                    "id": "email-branding-1-id",
                    "colour": "#f00",
                    "brand_type": "org",
                },
                {
                    "logo": "example_2.png",
                    "name": "Email branding name 2",
                    "text": "Email branding text 2",
                    "id": "email-branding-2-id",
                    "colour": "#f00",
                    "brand_type": "org",
                },
            ],
            [
                ("govuk", "GOV.UK"),
                ("govuk_and_org", "GOV.UK and Test Organisation"),
                ("email-branding-2-id", "Email branding name 2"),
            ],
        ),
        (
            [
                {
                    "logo": "example_1.png",
                    "name": "GOV.UK and test organisation",
                    "text": "test organisation",
                    "id": "govuk-and-org-id",
                    "colour": None,
                    "brand_type": "both",
                },
            ],
            [
                ("govuk", "GOV.UK"),
                ("govuk-and-org-id", "GOV.UK and test organisation"),
            ],
        ),
    ),
)
def test_current_email_branding_is_not_displayed_in_email_branding_pool_options(
    mocker,
    service_one,
    mock_get_email_branding_pool,
    mock_get_service_organisation,
    mock_get_email_branding,
    branding_pool,
    expected_options,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(organisation_type="central")
    )
    mocker.patch(
        "app.models.service.Service.email_branding_id",
        new_callable=PropertyMock,
        return_value="email-branding-1-id",
    )

    mocker.patch("app.models.branding.EmailBrandingPool.client_method", return_value=branding_pool)

    options = get_email_choices(service)
    assert list(options) == expected_options


@pytest.mark.parametrize(
    "org_type, branding_id, expected_options",
    [
        ("central", None, [("organisation", "Test Organisation")]),
        ("local", None, [("organisation", "Test Organisation")]),
        ("local", "some-random-branding", [("organisation", "Test Organisation")]),
        ("nhs_central", None, [(LetterBranding.NHS_ID, "NHS"), ("organisation", "Test Organisation")]),
    ],
)
def test_get_letter_choices_service_assigned_to_org(
    mocker,
    service_one,
    org_type,
    branding_id,
    expected_options,
    mock_get_service_organisation,
    mock_get_empty_letter_branding_pool,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(organisation_type=org_type)
    )
    mocker.patch(
        "app.models.service.Service.letter_branding_id",
        new_callable=PropertyMock,
        return_value=branding_id,
    )

    options = get_letter_choices(service)
    assert list(options) == expected_options


def test_get_letter_choices_shows_org_branding_if_org_has_empty_pool(
    mocker,
    service_one,
    mock_get_service_organisation,
    mock_get_empty_letter_branding_pool,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(organisation_type="central", letter_branding_id="org-branding-id"),
    )
    mocker.patch(
        "app.models.service.Service.letter_branding_id", new_callable=PropertyMock, return_value="some-branding-id"
    )
    options = get_letter_choices(service)
    assert list(options) == [
        ("organisation", "Test Organisation"),
    ]


@pytest.mark.parametrize(
    "branding_name, expected_options",
    [
        (
            "NHS something else",
            [
                (LetterBranding.NHS_ID, "NHS"),
                ("organisation", "Test Organisation"),
            ],
        ),
        (
            "NHS",
            [
                # don't show NHS option if it's the current branding
                ("organisation", "Test Organisation"),
            ],
        ),
    ],
)
def test_get_letter_choices_shows_nhs_branding_for_nhs_services(
    mocker,
    service_one,
    branding_name,
    expected_options,
    mock_get_service_organisation,
    mock_get_empty_letter_branding_pool,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(organisation_type="nhs_central")
    )
    mocker.patch(
        "app.models.service.Service.letter_branding_id",
        new_callable=PropertyMock,
        return_value="org-branding-id",
    )
    mocker.patch("app.letter_branding_client.get_letter_branding", return_value={"name": branding_name})

    options = get_letter_choices(service)
    assert list(options) == expected_options


def test_current_letter_branding_is_not_displayed_in_letter_branding_pool_options(
    mocker,
    service_one,
    mock_get_letter_branding_pool,
    mock_get_service_organisation,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(organisation_type="central")
    )
    mocker.patch(
        "app.models.service.Service.letter_branding_id",
        new_callable=PropertyMock,
        side_effect=["letter-branding-1-id"],
    )

    branding_pool = [
        {
            "filename": "example_1.png",
            "name": "Letter branding name 1",
            "id": "letter-branding-1-id",
        },
        {
            "filename": "example_2.png",
            "name": "Letter branding name 2",
            "id": "letter-branding-2-id",
        },
    ]

    # note: no organisation option visible since the org already has a branding pool
    expected_options = [
        ("letter-branding-2-id", "Letter branding name 2"),
    ]
    mocker.patch("app.models.branding.LetterBrandingPool.client_method", return_value=branding_pool)

    options = get_letter_choices(service)
    assert list(options) == expected_options
