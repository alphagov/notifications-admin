import uuid

from app.notify_client.billing_api_client import BillingAPIClient


def test_get_billing_units_calls_correct_endpoint(mocker, api_user_active):
    service_id = uuid.uuid4()
    expected_url = '/service/{}/billing/monthly-usage'.format(service_id)

    client = BillingAPIClient()

    mock_get = mocker.patch('app.notify_client.billing_api_client.BillingAPIClient.get')

    client.get_billable_units(service_id, 2017)
    mock_get.assert_called_once_with(expected_url, params={'year': 2017})


def test_get_get_service_usage_calls_correct_endpoint(mocker, api_user_active):
    service_id = uuid.uuid4()
    expected_url = '/service/{}/billing/yearly-usage-summary'.format(service_id)

    client = BillingAPIClient()

    mock_get = mocker.patch('app.notify_client.billing_api_client.BillingAPIClient.get')

    client.get_service_usage(service_id, 2017)
    mock_get.assert_called_once_with(expected_url, params={'year': 2017})
