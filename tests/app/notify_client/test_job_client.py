import uuid
from unittest.mock import ANY

import pytest

from app.models.job import Job, PaginatedJobs
from app.notify_client.job_api_client import JobApiClient


def test_client_creates_job_data_correctly(mocker, fake_uuid):
    job_id = fake_uuid
    service_id = fake_uuid
    mocker.patch('app.notify_client.current_user', id='1')
    mock_redis_set = mocker.patch('app.extensions.RedisClient.set')

    expected_data = {
        "id": job_id,
        "created_by": '1'
    }

    expected_url = '/service/{}/job'.format(service_id)

    client = JobApiClient()
    mock_post = mocker.patch(
        'app.notify_client.job_api_client.JobApiClient.post',
        return_value={'data': dict(statistics=[], **expected_data)}
    )

    client.create_job(service_id, job_id)
    mock_post.assert_called_once_with(url=expected_url, data=expected_data)
    mock_redis_set.assert_called_once_with(
        'has_jobs-{}'.format(service_id),
        b'true',
        ex=604800,
    )


def test_client_schedules_job(mocker, fake_uuid):

    mocker.patch('app.notify_client.current_user', id='1')

    mock_post = mocker.patch('app.notify_client.job_api_client.JobApiClient.post')

    when = '2016-08-25T13:04:21.767198'

    JobApiClient().create_job(
        fake_uuid, 1, scheduled_for=when
    )

    assert mock_post.call_args[1]['data']['scheduled_for'] == when


def test_client_links_job_to_contact_list(mocker, fake_uuid):

    mocker.patch('app.notify_client.current_user', id='1')

    contact_list_id = uuid.uuid4()

    mock_post = mocker.patch('app.notify_client.job_api_client.JobApiClient.post')

    JobApiClient().create_job(
        fake_uuid, 1, contact_list_id=contact_list_id
    )

    assert mock_post.call_args[1]['data']['contact_list_id'] == contact_list_id


def test_client_gets_job_by_service_and_job(mocker):
    service_id = 'service_id'
    job_id = 'job_id'

    expected_url = '/service/{}/job/{}'.format(service_id, job_id)

    client = JobApiClient()
    mock_get = mocker.patch('app.notify_client.job_api_client.JobApiClient.get')

    client.get_job(service_id, job_id)

    mock_get.assert_called_once_with(url=expected_url, params={})


def test_client_gets_jobs_with_status_filter(mocker):
    mock_get = mocker.patch('app.notify_client.job_api_client.JobApiClient.get')

    JobApiClient().get_jobs(uuid.uuid4(), statuses=['foo', 'bar'])

    mock_get.assert_called_once_with(url=ANY, params={'page': 1, 'statuses': 'foo,bar'})


def test_client_gets_jobs_with_page_parameter(mocker):
    client = JobApiClient()
    mock_get = mocker.patch('app.notify_client.job_api_client.JobApiClient.get')

    client.get_jobs('foo', page=2)

    mock_get.assert_called_once_with(url=ANY, params={'page': 2})


def test_client_parses_job_stats(mocker):
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

    mock_get = mocker.patch('app.notify_client.job_api_client.JobApiClient.get', return_value=expected_data)

    result = Job.from_id(job_id, service_id=service_id)

    mock_get.assert_called_once_with(url=expected_url, params={})
    assert result.notifications_requested == 80
    assert result.notifications_sent == 50
    assert result.notification_count == 80
    assert result.notifications_failed == 40


def test_client_parses_empty_job_stats(mocker):
    service_id = 'service_id'
    job_id = 'job_id'
    expected_data = {'data': {
        'status': 'finished',
        'template_version': 3,
        'id': job_id,
        'updated_at': '2016-08-24T08:29:28.332972+00:00',
        'service': service_id,
        'processing_finished': '2016-08-24T08:11:48.676365+00:00',
        'statistics': [],
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

    mock_get = mocker.patch('app.notify_client.job_api_client.JobApiClient.get', return_value=expected_data)

    result = Job.from_id(job_id, service_id=service_id)

    mock_get.assert_called_once_with(url=expected_url, params={})
    assert result.notifications_requested == 0
    assert result.notifications_sent == 0
    assert result.notification_count == 80
    assert result.notifications_failed == 0


def test_client_parses_job_stats_for_service(mocker):
    service_id = 'service_id'
    job_1_id = 'job_id_1'
    job_2_id = 'job_id_2'
    expected_data = {'data': [{
        'status': 'finished',
        'template_version': 3,
        'id': job_1_id,
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
    }, {
        'status': 'finished',
        'template_version': 3,
        'id': job_2_id,
        'updated_at': '2016-08-24T08:29:28.332972+00:00',
        'service': service_id,
        'processing_finished': '2016-08-24T08:11:48.676365+00:00',
        'statistics': [
            {'status': 'failed', 'count': 5},
            {'status': 'technical-failure', 'count': 5},
            {'status': 'temporary-failure', 'count': 5},
            {'status': 'permanent-failure', 'count': 5},
            {'status': 'created', 'count': 5},
            {'status': 'sending', 'count': 5},
            {'status': 'pending', 'count': 5},
            {'status': 'delivered', 'count': 5}
        ],
        'original_file_name': 'test-notify-email.csv',
        'created_by': {
            'name': 'test-user@digital.cabinet-office.gov.uk',
            'id': '3571f2ae-7a39-4fb4-9ad7-8453f5257072'
        },
        'created_at': '2016-08-24T08:09:56.371073+00:00',
        'template': 'c0309261-9c9e-4530-8fed-5f67b02260d2',
        'notification_count': 40,
        'processing_started': '2016-08-24T08:09:57.661246+00:00'
    }]}

    expected_url = '/service/{}/job'.format(service_id)

    mock_get = mocker.patch('app.notify_client.job_api_client.JobApiClient.get', return_value=expected_data)

    result = PaginatedJobs(service_id)

    mock_get.assert_called_once_with(url=expected_url, params={'page': 1, 'statuses': ANY})
    assert result[0].id == job_1_id
    assert result[0].notifications_requested == 80
    assert result[0].notifications_sent == 50
    assert result[0].notification_count == 80
    assert result[0].notifications_failed == 40
    assert result[1].id == job_2_id
    assert result[1].notifications_requested == 40
    assert result[1].notifications_sent == 25
    assert result[1].notification_count == 40
    assert result[1].notifications_failed == 20


def test_client_parses_empty_job_stats_for_service(mocker):
    service_id = 'service_id'
    job_1_id = 'job_id_1'
    job_2_id = 'job_id_2'
    expected_data = {'data': [{
        'status': 'finished',
        'template_version': 3,
        'id': job_1_id,
        'updated_at': '2016-08-24T08:29:28.332972+00:00',
        'service': service_id,
        'processing_finished': '2016-08-24T08:11:48.676365+00:00',
        'statistics': [],
        'original_file_name': 'test-notify-email.csv',
        'created_by': {
            'name': 'test-user@digital.cabinet-office.gov.uk',
            'id': '3571f2ae-7a39-4fb4-9ad7-8453f5257072'
        },
        'created_at': '2016-08-24T08:09:56.371073+00:00',
        'template': 'c0309261-9c9e-4530-8fed-5f67b02260d2',
        'notification_count': 80,
        'processing_started': '2016-08-24T08:09:57.661246+00:00'
    }, {
        'status': 'finished',
        'template_version': 3,
        'id': job_2_id,
        'updated_at': '2016-08-24T08:29:28.332972+00:00',
        'service': service_id,
        'processing_finished': '2016-08-24T08:11:48.676365+00:00',
        'statistics': [],
        'original_file_name': 'test-notify-email.csv',
        'created_by': {
            'name': 'test-user@digital.cabinet-office.gov.uk',
            'id': '3571f2ae-7a39-4fb4-9ad7-8453f5257072'
        },
        'created_at': '2016-08-24T08:09:56.371073+00:00',
        'template': 'c0309261-9c9e-4530-8fed-5f67b02260d2',
        'notification_count': 40,
        'processing_started': '2016-08-24T08:09:57.661246+00:00'
    }]}

    expected_url = '/service/{}/job'.format(service_id)

    mock_get = mocker.patch('app.notify_client.job_api_client.JobApiClient.get', return_value=expected_data)

    result = PaginatedJobs(service_id)

    mock_get.assert_called_once_with(url=expected_url, params={'page': 1, 'statuses': ANY})
    assert result[0].id == job_1_id
    assert result[0].notifications_requested == 0
    assert result[0].notifications_sent == 0
    assert result[0].notification_count == 80
    assert result[0].notifications_failed == 0
    assert result[1].id == job_2_id
    assert result[1].notifications_requested == 0
    assert result[1].notifications_sent == 0
    assert result[1].notification_count == 40
    assert result[1].notifications_failed == 0


def test_cancel_job(mocker):
    mock_post = mocker.patch('app.notify_client.job_api_client.JobApiClient.post')

    JobApiClient().cancel_job('service_id', 'job_id')

    mock_post.assert_called_once_with(
        url='/service/{}/job/{}/cancel'.format('service_id', 'job_id'),
        data={}
    )


@pytest.mark.parametrize('job_data, expected_cache_value', [
    (
        [{'data': [1, 2, 3], 'statistics': []}],
        'true',
    ),
    (
        [],
        'false',
    ),
])
def test_has_jobs_sets_cache(
    mocker,
    fake_uuid,
    job_data,
    expected_cache_value,
):
    mock_get = mocker.patch(
        'app.notify_client.job_api_client.JobApiClient.get',
        return_value={'data': job_data}
    )
    mock_redis_set = mocker.patch('app.extensions.RedisClient.set')

    JobApiClient().has_jobs(fake_uuid)

    mock_get.assert_called_once_with(
        url='/service/{}/job'.format(fake_uuid),
        params={'page': 1}
    )
    mock_redis_set.assert_called_once_with(
        'has_jobs-{}'.format(fake_uuid),
        expected_cache_value,
        ex=604800,
    )


@pytest.mark.parametrize('cache_value, return_value', [
    (b'true', True),
    (b'false', False),
])
def test_has_jobs_returns_from_cache(
    mocker,
    fake_uuid,
    cache_value,
    return_value,
):
    mock_get = mocker.patch(
        'app.notify_client.job_api_client.JobApiClient.get'
    )
    mock_redis_get = mocker.patch(
        'app.extensions.RedisClient.get',
        return_value=cache_value,
    )

    assert JobApiClient().has_jobs(fake_uuid) is return_value
    assert not mock_get.called
    mock_redis_get.assert_called_once_with(
        'has_jobs-{}'.format(fake_uuid)
    )
