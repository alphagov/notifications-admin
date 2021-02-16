import pytest

from app.models.organisation import Organisation
from tests import organisation_json


@pytest.mark.parametrize("purchase_order_number,expected_result", [
    [None, None],
    ["PO1234", [None, None, None, "PO1234"]]
])
def test_organisation_billing_details(purchase_order_number, expected_result):
    organisation = Organisation(organisation_json(purchase_order_number=purchase_order_number))
    assert organisation.billing_details == expected_result
