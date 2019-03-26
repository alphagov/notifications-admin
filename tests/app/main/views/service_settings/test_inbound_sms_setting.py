from tests.conftest import SERVICE_ONE_ID, normalize_spaces


def test_set_inbound_sms_sets_a_number_for_service(
    client_request,
    mock_add_sms_sender,
    multiple_available_inbound_numbers,
    fake_uuid,
    mock_no_inbound_number_for_service,
    mocker
):
    mocker.patch('app.service_api_client.update_service')
    data = {
        "inbound_number": "781d9c60-7a7e-46b7-9896-7b045b992fa5",
    }

    client_request.post(
        'main.service_set_inbound_number',
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=302,
    )

    mock_add_sms_sender.assert_called_once_with(
        SERVICE_ONE_ID,
        sms_sender="781d9c60-7a7e-46b7-9896-7b045b992fa5",
        is_default=True,
        inbound_number_id="781d9c60-7a7e-46b7-9896-7b045b992fa5"
    )


def test_set_inbound_sms_when_no_available_inbound_numbers(
        client_request,
        service_one,
        no_available_inbound_numbers,
        mock_no_inbound_number_for_service,
        mocker
):
    page = client_request.get(
        'main.service_set_inbound_number',
        service_id=service_one['id']
    )

    assert normalize_spaces(page.select_one('main p').text) == "No available inbound numbers"


def test_set_inbound_sms_when_service_already_has_sms(
    client_request,
    service_one,
    multiple_available_inbound_numbers,
    mock_get_inbound_number_for_service,
):

    page = client_request.get(
        'main.service_set_inbound_number',
        service_id=service_one['id']
    )

    assert normalize_spaces(page.select_one('main p').text) == "This service already has an inbound number"


def test_set_inbound_sms_when_service_does_not_have_sms(
    client_request,
    service_one,
    multiple_available_inbound_numbers,
    mock_no_inbound_number_for_service,
):

    page = client_request.get(
        'main.service_set_inbound_number',
        service_id=service_one['id']
    )

    assert normalize_spaces(page.select_one('input')['name']) == "inbound_number"
