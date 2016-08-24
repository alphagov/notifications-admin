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


def test_client_gets_job_by_service_and_job(mocker):
    mocker.patch('app.notify_client.current_user', id='1')

    service_id = 'service_id'
    job_id = 'job_id'

    expected_url = '/service/{}/job/{}'.format(service_id, job_id)

    client = JobApiClient()
    mock_get = mocker.patch('app.notify_client.job_api_client.JobApiClient.get')

    client.get_job(service_id, job_id)

    mock_get.assert_called_once_with(url=expected_url, params={})


def test_client_gets_job_by_service_and_job_filtered_by_status(mocker):
    mocker.patch('app.notify_client.current_user', id='1')

    service_id = 'service_id'
    job_id = 'job_id'

    expected_url = '/service/{}/job/{}'.format(service_id, job_id)

    client = JobApiClient()
    mock_get = mocker.patch('app.notify_client.job_api_client.JobApiClient.get')

    client.get_job(service_id, job_id, limit_days=1, status='failed')

    mock_get.assert_called_once_with(url=expected_url, params={'status': 'failed'})


def test_client_gets_job_by_service_filtered_by_status(mocker):
    mocker.patch('app.notify_client.current_user', id='1')

    service_id = 'service_id'

    expected_url = '/service/{}/job'.format(service_id)

    client = JobApiClient()
    mock_get = mocker.patch('app.notify_client.job_api_client.JobApiClient.get')

    client.get_job(service_id, limit_days=1, status='failed')

    mock_get.assert_called_once_with(url=expected_url,  params={'limit_days': 1})


def test_client_parses_handles_aggregate_table_job_stats(mocker):
    mocker.patch('app.notify_client.current_user', id='1')

    service_id = 'service_id'
    job_id = 'job_id'
    expected_data = {'data': {
        'status': 'finished',
        'template_version': 3,
        'id': job_id,
        'updated_at': '2016-08-24T08:29:28.332972+00:00',
        'service': service_id,
        'processing_finished': '2016-08-24T08:11:48.676365+00:00',
        'original_file_name': 'test-notify-email.csv',
        'created_by': {
            'name': 'test-user@digital.cabinet-office.gov.uk',
            'id': '3571f2ae-7a39-4fb4-9ad7-8453f5257072'
        },
        'created_at': '2016-08-24T08:09:56.371073+00:00',
        'template': 'c0309261-9c9e-4530-8fed-5f67b02260d2',
        'notification_count': 30,
        'notifications_sent': 10,
        'notifications_failed': 10,
        'notifications_delivered': 10,
        'processing_started': '2016-08-24T08:09:57.661246+00:00'
    }}

    expected_url = '/service/{}/job/{}'.format(service_id, job_id)

    client = JobApiClient()
    mock_get = mocker.patch('app.notify_client.job_api_client.JobApiClient.get', return_value=expected_data)

    result = client.get_job(service_id, job_id)

    mock_get.assert_called_once_with(url=expected_url, params={})
    assert result['data']['notifications_sent'] == 10
    assert result['data']['notification_count'] == 30
    assert result['data']['notifications_failed'] == 10


def test_client_parses_job_stats(mocker):
    mocker.patch('app.notify_client.current_user', id='1')

    service_id = 'service_id'
    job_id = 'job_id'
    expected_data = {'data': {
        'status': 'finished',
        'template_version': 3,
        'id': job_id,
        'updated_at': '2016-08-24T08:29:28.332972+00:00',
        'service': service_id,
        'processing_finished': '2016-08-24T08:11:48.676365+00:00',
        'statistics': [
            {'status': 'failed', 'count': 10},
            {'status': 'technical-failure', 'count': 10},
            {'status': 'temporary-failure', 'count': 10},
            {'status': 'permanent-failure', 'count': 10},
            {'status': 'created', 'count': 10},
            {'status': 'sending', 'count': 10},
            {'status': 'pending', 'count': 10},
            {'status': 'delivered', 'count': 10}
        ],
        'original_file_name': 'test-notify-email.csv',
        'created_by': {
            'name': 'test-user@digital.cabinet-office.gov.uk',
            'id': '3571f2ae-7a39-4fb4-9ad7-8453f5257072'
        },
        'created_at': '2016-08-24T08:09:56.371073+00:00',
        'template': 'c0309261-9c9e-4530-8fed-5f67b02260d2',
        'notification_count': 80,
        'processing_started': '2016-08-24T08:09:57.661246+00:00'
    }}

    expected_url = '/service/{}/job/{}'.format(service_id, job_id)

    client = JobApiClient()
    mock_get = mocker.patch('app.notify_client.job_api_client.JobApiClient.get', return_value=expected_data)

    result = client.get_job(service_id, job_id)

    mock_get.assert_called_once_with(url=expected_url, params={})
    assert result['data']['notifications_sent'] == 50
    assert result['data']['notification_count'] == 80
    assert result['data']['notifications_failed'] == 40
