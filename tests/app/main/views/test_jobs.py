import pytest
from flask import url_for
from bs4 import BeautifulSoup
import json
from app.utils import generate_notifications_csv
from tests import (notification_json, job_json)
from tests.conftest import fake_uuid
from tests.conftest import mock_get_job as mock_get_job1
from freezegun import freeze_time


def test_should_return_list_of_all_jobs(app_,
                                        service_one,
                                        active_user_with_permissions,
                                        mock_get_jobs,
                                        mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            response = client.get(url_for('main.view_jobs', service_id=service_one['id']))

        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.h1.string == 'Uploaded files'
        jobs = page.tbody.find_all('tr')
        assert len(jobs) == 5


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_page_for_one_job(
    app_,
    service_one,
    active_user_with_permissions,
    mock_get_service_template,
    mock_get_job,
    mocker,
    mock_get_notifications,
    fake_uuid
):
    file_name = mock_get_job(service_one['id'], fake_uuid)['data']['original_file_name']
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            response = client.get(url_for('main.view_job', service_id=service_one['id'], job_id=fake_uuid))

        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert "{}: Your vehicle tax is about to expire".format(service_one['name']) in content
        assert file_name in content
        assert "Delivered at 11:10" in content


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_updates_for_one_job_as_json(
    app_,
    service_one,
    active_user_with_permissions,
    mock_get_notifications,
    mock_get_job,
    mocker,
    fake_uuid
):
    job_json = mock_get_job(service_one['id'], fake_uuid)['data']
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            response = client.get(url_for('main.view_job_updates', service_id=service_one['id'], job_id=fake_uuid))

        assert response.status_code == 200
        content = json.loads(response.get_data(as_text=True))
        assert 'sending' in content['counts']
        assert 'delivered' in content['counts']
        assert 'failed' in content['counts']
        assert 'Recipient' in content['notifications']
        assert '07123456789' in content['notifications']
        assert 'Status' in content['notifications']
        assert job_json['status'] in content['status']
        assert 'Delivered at 11:10' in content['notifications']
        assert 'Uploaded by Test User on 1 January at 11:09' in content['status']


@pytest.mark.parametrize(
    "message_type,page_title", [
        ('email', 'Emails'),
        ('sms', 'Text messages')
    ]
)
@pytest.mark.parametrize(
    "status_argument, expected_api_call", [
        (
            'processed',
            ['sending', 'delivered', 'failed', 'temporary-failure', 'permanent-failure', 'technical-failure']
        ),
        (
            'sending',
            ['sending']
        ),
        (
            'delivered',
            ['delivered']
        ),
        (
            'failed',
            ['failed', 'temporary-failure', 'permanent-failure', 'technical-failure']
        )
    ]
)
def test_can_show_notifications(
    app_,
    service_one,
    active_user_with_permissions,
    mock_get_notifications,
    mocker,
    message_type,
    page_title,
    status_argument,
    expected_api_call
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            response = client.get(url_for(
                'main.view_notifications',
                service_id=service_one['id'],
                message_type=message_type,
                status=status_argument))
        assert response.status_code == 200
        content = response.get_data(as_text=True)

        notifications = notification_json(service_one['id'])
        notification = notifications['notifications'][0]
        assert notification['to'] in content
        assert notification['status'] in content
        assert notification['template']['name'] in content
        assert 'csv' in content
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page_title in page.h1.text.strip()
        assert url_for(
            '.view_notifications_csv',
            service_id=service_one['id'],
            message_type=message_type,
            status=status_argument
        ) == page.findAll("a", {"download": "download"})[0]['href']

        mock_get_notifications.assert_called_with(
            limit_days=7,
            page=1,
            service_id=service_one['id'],
            status=expected_api_call,
            template_type=[message_type]
        )

        csv_response = client.get(url_for(
            'main.view_notifications_csv',
            service_id=service_one['id'],
            message_type='email',
            download='csv'
        ))
        csv_content = generate_notifications_csv(
            mock_get_notifications(service_one['id'])['notifications']
        )
        assert csv_response.status_code == 200
        assert csv_response.get_data(as_text=True) == csv_content
        assert 'text/csv' in csv_response.headers['Content-Type']


def test_should_show_notifications_for_a_service_with_next_previous(app_,
                                                                    service_one,
                                                                    active_user_with_permissions,
                                                                    mock_get_notifications_with_previous_next,
                                                                    mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            response = client.get(url_for(
                'main.view_notifications',
                service_id=service_one['id'],
                message_type='sms',
                page=2
            ))
        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert url_for('main.view_notifications', service_id=service_one['id'], message_type='sms', page=3) in content
        assert url_for('main.view_notifications', service_id=service_one['id'], message_type='sms', page=1) in content
        assert 'Previous page' in content
        assert 'Next page' in content


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_download_notifications_for_a_job(app_,
                                                 api_user_active,
                                                 mock_login,
                                                 mock_get_service,
                                                 mock_get_job,
                                                 mock_get_notifications,
                                                 mock_get_template_version,
                                                 mock_has_permissions,
                                                 fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for(
                'main.view_job_csv',
                service_id=fake_uuid,
                job_id=fake_uuid,
            ))
        csv_content = generate_notifications_csv(
            mock_get_notifications(fake_uuid, job_id=fake_uuid)['notifications']
        )
        assert response.status_code == 200
        assert response.get_data(as_text=True) == csv_content
        assert 'text/csv' in response.headers['Content-Type']
        assert 'sample template - 1 January at 11:09.csv"' in response.headers['Content-Disposition']
