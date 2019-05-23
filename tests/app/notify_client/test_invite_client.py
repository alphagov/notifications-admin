from unittest.mock import ANY

from app import invite_api_client


def test_client_creates_invite(
    app_,
    mocker,
    fake_uuid,
    sample_invite,
):

    mocker.patch('app.notify_client.current_user')

    mock_post = mocker.patch(
        'app.invite_api_client.post',
        return_value={'data': dict.fromkeys({
            'id', 'service', 'from_user', 'email_address',
            'permissions', 'status', 'created_at', 'auth_type', 'folder_permissions'
        })}
    )

    invite_api_client.create_invite(
        '12345', '67890', 'test@example.com', {'send_messages'}, 'sms_auth', [fake_uuid]
    )

    mock_post.assert_called_once_with(
        url='/service/{}/invite'.format('67890'),
        data={
            'auth_type': 'sms_auth',
            'email_address': 'test@example.com',
            'from_user': '12345',
            'service': '67890',
            'created_by': ANY,
            'permissions': 'send_emails,send_letters,send_texts',
            'invite_link_host': 'http://localhost:6012',
            'folder_permissions': [fake_uuid]
        }
    )


def test_client_returns_invite(mocker, sample_invite):

    sample_invite['status'] = 'pending'
    service_id = sample_invite['service']

    expected_data = {'data': [sample_invite]}

    expected_url = '/service/{}/invite'.format(service_id)

    mock_get = mocker.patch('app.notify_client.invite_api_client.InviteApiClient.get', return_value=expected_data)

    invites = invite_api_client.get_invites_for_service(service_id)

    mock_get.assert_called_once_with(expected_url)
    assert len(invites) == 1
    assert invites[0]['status'] == 'pending'
