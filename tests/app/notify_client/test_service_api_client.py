import pytest

from app.notify_client.service_api_client import ServiceAPIClient
from tests.conftest import fake_uuid


def test_client_posts_archived_true_when_deleting_template(mocker):
    service_id = fake_uuid
    template_id = fake_uuid

    expected_data = {
        'archived': True,
        'created_by': fake_uuid
    }
    expected_url = '/service/{}/template/{}'.format(service_id, template_id)

    client = ServiceAPIClient()
    mock_post = mocker.patch('app.notify_client.service_api_client.ServiceAPIClient.post')
    mock_attach_user = mocker.patch('app.notify_client.service_api_client._attach_current_user',
                                    side_effect=lambda x: x.update({'created_by': fake_uuid}))

    client.delete_service_template(service_id, template_id)
    mock_post.assert_called_once_with(expected_url, data=expected_data)


@pytest.mark.parametrize(
    'function,params', [
        (ServiceAPIClient.get_service, {}),
        (ServiceAPIClient.get_detailed_service, {'detailed': True}),
        (ServiceAPIClient.get_detailed_service_for_today, {'detailed': True, 'today_only': True})
    ],
    ids=lambda x: x.__name__
)
def test_client_gets_service(mocker, function, params):
    client = ServiceAPIClient()
    mock_post = mocker.patch.object(client, 'get')

    function(client, 'foo')
    mock_post.assert_called_once_with('/service/foo', params=params)
