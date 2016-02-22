from app.notify_client.job_api_client import JobApiClient


def test_client_creates_job_data_correctly(mocker):
    import uuid
    job_id = str(uuid.uuid4())
    service_id = str(uuid.uuid4())
    template_id = 1
    original_file_name = 'test.csv'
    notification_count = 1

    expected_data = {
        "id": job_id,
        "service": service_id,
        "template": template_id,
        "original_file_name": original_file_name,
        "bucket_name": "service-{}-notify".format(service_id),
        "file_name": "{}.csv".format(job_id),
        "notification_count": 1
    }

    expected_url = '/service/{}/job'.format(service_id)

    client = JobApiClient()
    mock_post = mocker.patch('app.notify_client.job_api_client.JobApiClient.post')

    client.create_job(job_id, service_id, template_id, original_file_name, notification_count)

    mock_post.assert_called_once_with(url=expected_url, data=expected_data)
