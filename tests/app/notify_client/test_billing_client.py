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


def test_get_free_sms_fragment_limit_for_current_year_correct_endpoint(mocker, api_user_active):
    service_id = uuid.uuid4()
    expected_url = '/service/{}/billing/free-sms-fragment-limit/current-year'.format(service_id)
    client = BillingAPIClient()

    mock_get = mocker.patch('app.notify_client.billing_api_client.BillingAPIClient.get')

    client.get_free_sms_fragment_limit_for_year(service_id)
    mock_get.assert_called_once_with(expected_url)


def test_get_free_sms_fragment_limit_for_year_correct_endpoint(mocker, api_user_active):
    service_id = uuid.uuid4()
    expected_url = '/service/{}/billing/free-sms-fragment-limit'.format(service_id)
    client = BillingAPIClient()

    mock_get = mocker.patch('app.notify_client.billing_api_client.BillingAPIClient.get')

    client.get_free_sms_fragment_limit_for_year(service_id, year=1999)
    mock_get.assert_called_once_with(expected_url, params={'financial_year_start': 1999})


def test_post_free_sms_fragment_limit_for_current_year_endpoint(mocker, api_user_active):
    service_id = uuid.uuid4()
    sms_limit_data = {'free_sms_fragment_limit': 1111}
    mock_post = mocker.patch('app.notify_client.billing_api_client.BillingAPIClient.post')
    client = BillingAPIClient()

    client.create_or_update_free_sms_fragment_limit_for_year(service_id=service_id, free_sms_fragment_limit=1111)

    mock_post.assert_called_once_with(
        url='/service/{}/billing/free-sms-fragment-limit'.format(service_id),
        data=sms_limit_data
    )


def test_post_free_sms_fragment_limit_for_year_endpoint(mocker, api_user_active):
    service_id = uuid.uuid4()
    sms_limit_data = {'free_sms_fragment_limit': 1111, 'financial_year_start': 2017}
    mock_post = mocker.patch('app.notify_client.billing_api_client.BillingAPIClient.post')
    client = BillingAPIClient()

    client.create_or_update_free_sms_fragment_limit_for_year(service_id=service_id,
                                                             free_sms_fragment_limit=1111,
                                                             year=2017)
    mock_post.assert_called_once_with(
        url='/service/{}/billing/free-sms-fragment-limit'.format(service_id),
        data=sms_limit_data
    )
