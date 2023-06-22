import pytest

from app.constants import PERMISSION_CAN_MAKE_SERVICES_LIVE
from app.models.organisation import Organisation
from tests import organisation_json


@pytest.mark.parametrize(
    "purchase_order_number,expected_result", [[None, None], ["PO1234", [None, None, None, "PO1234"]]]
)
def test_organisation_billing_details(purchase_order_number, expected_result):
    organisation = Organisation(organisation_json(purchase_order_number=purchase_order_number))
    assert organisation.billing_details == expected_result


@pytest.mark.parametrize("can_approve_own_go_live_requests", (True, False))
def test_can_use_org_user_permissions(can_approve_own_go_live_requests):
    organisation = Organisation(organisation_json(can_approve_own_go_live_requests=can_approve_own_go_live_requests))
    assert (
        organisation.can_use_org_user_permission(PERMISSION_CAN_MAKE_SERVICES_LIVE) is can_approve_own_go_live_requests
    )
