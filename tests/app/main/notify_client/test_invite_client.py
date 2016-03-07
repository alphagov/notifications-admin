from app.notify_client.invite_api_client import InviteApiClient


def test_client_returns_invite(mocker, sample_invite):

    sample_invite['status'] = 'pending'
    service_id = sample_invite['service']

    expected_data = {'data': [sample_invite]}

    expected_url = '/service/{}/invite'.format(service_id)

    client = InviteApiClient()
    mock_get = mocker.patch('app.notify_client.invite_api_client.InviteApiClient.get', return_value=expected_data)

    invites = client.get_invites_for_service(service_id)

    mock_get.assert_called_once_with(expected_url)
    assert len(invites) == 1
    assert invites[0].status == 'pending'


def test_client_filters_out_accepted_invites(mocker, sample_invite):

    sample_invite['status'] = 'accepted'
    service_id = sample_invite['service']

    expected_data = {'data': [sample_invite]}

    expected_url = '/service/{}/invite'.format(service_id)

    client = InviteApiClient()
    mock_get = mocker.patch('app.notify_client.invite_api_client.InviteApiClient.get', return_value=expected_data)

    invites = client.get_invites_for_service(service_id)

    mock_get.assert_called_once_with(expected_url)
    assert len(invites) == 0
