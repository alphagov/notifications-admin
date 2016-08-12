from app.notify_client.job_api_client import JobApiClient


def test_client_creates_job_data_correctly(mocker, fake_uuid):
    job_id = fake_uuid
    service_id = fake_uuid
    template_id = fake_uuid
    original_file_name = 'test.csv'
    notification_count = 1
    mocker.patch('app.notify_client.current_user', id='1')

    expected_data = {
        "id": job_id,
        "template": template_id,
        "original_file_name": original_file_name,
        "notification_count": 1,
        "created_by": '1'
    }

    expected_url = '/service/{}/job'.format(service_id)

    client = JobApiClient()
    mock_post = mocker.patch('app.notify_client.job_api_client.JobApiClient.post')

    client.create_job(job_id, service_id, template_id, original_file_name, notification_count)

    mock_post.assert_called_once_with(url=expected_url, data=expected_data)
