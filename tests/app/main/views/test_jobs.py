import json
import uuid
from urllib.parse import urlparse, quote, parse_qs

import pytest
from flask import url_for
from bs4 import BeautifulSoup

from app.utils import generate_notifications_csv
from app.main.views.jobs import get_time_left, get_status_filters
from tests import notification_json
from freezegun import freeze_time


def test_get_jobs_should_return_list_of_all_real_jobs(
    client,
    service_one,
    active_user_with_permissions,
    mock_get_jobs,
    mocker
):
    client.login(active_user_with_permissions, mocker, service_one)
    response = client.get(url_for('main.view_jobs', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string == 'Uploaded files'
    jobs = [x.text for x in page.tbody.find_all('a', {'class': 'file-list-filename'})]
    assert len(jobs) == 4
    assert 'Test message' not in jobs


def test_get_jobs_shows_page_links(
    client,
    service_one,
    active_user_with_permissions,
    mock_get_jobs,
    mocker
):
    client.login(active_user_with_permissions, mocker, service_one)
    response = client.get(url_for('main.view_jobs', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Next page' in page.find('li', {'class': 'next-page'}).text
    assert 'Previous page' in page.find('li', {'class': 'previous-page'}).text


@pytest.mark.parametrize(
    "status_argument, expected_api_call", [
        (
            '',
            ['created', 'sending', 'delivered', 'failed', 'temporary-failure', 'permanent-failure', 'technical-failure']
        ),
        (
            'sending',
            ['sending', 'created']
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
@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_page_for_one_job(
    app_,
    service_one,
    active_user_with_permissions,
    mock_get_service_template,
    mock_get_job,
    mocker,
    mock_get_notifications,
    fake_uuid,
    status_argument,
    expected_api_call
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(active_user_with_permissions, mocker, service_one)
        response = client.get(url_for(
            'main.view_job',
            service_id=service_one['id'],
            job_id=fake_uuid,
            status=status_argument
        ))

        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.h1.text.strip() == 'thisisatest.csv'
        assert page.find('div', {'class': 'sms-message-wrapper'}).text.strip() == (
            '{}: Your vehicle tax is about to expire'.format(service_one['name'])
        )
        assert ' '.join(page.find('tbody').find('tr').text.split()) == (
            '07123456789 Delivered 1 January at 11:10am'
        )
        assert page.find('div', {'data-key': 'notifications'})['data-resource'] == url_for(
            'main.view_job_updates',
            service_id=service_one['id'],
            job_id=fake_uuid,
            status=status_argument,
        )
        csv_link = page.find('a', {'download': 'download'})
        assert csv_link['href'] == url_for(
            'main.view_job_csv',
            service_id=service_one['id'],
            job_id=fake_uuid,
            status=status_argument
        )
        assert csv_link.text == 'Download this report'
        assert page.find('span', {'id': 'time-left'}).text == 'Data available for 7 days'
        assert page.find('p', {'class': 'table-show-more-link'}).text.strip() == 'Only showing the first 50 rows'
        mock_get_notifications.assert_called_with(
            service_one['id'],
            fake_uuid,
            status=expected_api_call
        )


def test_should_show_job_in_progress(
    app_,
    service_one,
    active_user_with_permissions,
    mock_get_service_template,
    mock_get_job_in_progress,
    mocker,
    mock_get_notifications,
    fake_uuid
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(active_user_with_permissions, mocker, service_one)
        response = client.get(url_for(
            'main.view_job',
            service_id=service_one['id'],
            job_id=fake_uuid
        ))

        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.find('p', {'class': 'hint'}).text.strip() == 'Report is 50% complete…'


def test_should_show_scheduled_job(
    app_,
    service_one,
    active_user_with_permissions,
    mock_get_service_template,
    mock_get_scheduled_job,
    mocker,
    mock_get_notifications,
    fake_uuid
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(active_user_with_permissions, mocker, service_one)
        response = client.get(url_for(
            'main.view_job',
            service_id=service_one['id'],
            job_id=fake_uuid
        ))

        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.find('main').find_all('p')[2].text.strip() == 'Sending will start at midnight'
        assert page.find('input', {'type': 'submit', 'value': 'Cancel sending'})


def test_should_cancel_job(
    app_,
    service_one,
    active_user_with_permissions,
    fake_uuid,
    mocker
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(active_user_with_permissions, mocker, service_one)
        mock_cancel = mocker.patch('app.main.jobs.job_api_client.cancel_job')
        response = client.post(url_for(
            'main.cancel_job',
            service_id=service_one['id'],
            job_id=fake_uuid
        ))

        mock_cancel.assert_called_once_with(service_one['id'], fake_uuid)
        assert response.status_code == 302
        assert response.location == url_for('main.service_dashboard', service_id=service_one['id'], _external=True)


def test_should_not_show_cancelled_job(
    app_,
    service_one,
    active_user_with_permissions,
    mock_get_cancelled_job,
    mocker,
    fake_uuid
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(active_user_with_permissions, mocker, service_one)
        response = client.get(url_for(
            'main.view_job',
            service_id=service_one['id'],
            job_id=fake_uuid
        ))

        assert response.status_code == 404


def test_should_show_not_show_csv_download_in_tour(
    app_,
    service_one,
    active_user_with_permissions,
    mock_get_service_template,
    mock_get_job,
    mocker,
    mock_get_notifications,
    fake_uuid
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(active_user_with_permissions, mocker, service_one)
        response = client.get(url_for(
            'main.view_job',
            service_id=service_one['id'],
            job_id=fake_uuid,
            help=3
        ))

        assert response.status_code == 200
        assert url_for(
            'main.view_job_updates',
            service_id=service_one['id'],
            job_id=fake_uuid,
            status='',
            help=3
        ).replace('&', '&amp;') in response.get_data(as_text=True)
        assert url_for(
            'main.view_job_csv',
            service_id=service_one['id'],
            job_id=fake_uuid
        ) not in response.get_data(as_text=True)


@freeze_time("2016-01-01 00:00:00.000001")
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
        assert 'Delivered' in content['notifications']
        assert '12:01am' in content['notifications']
        assert 'Uploaded by Test User on 1 January at midnight' in content['status']


@pytest.mark.parametrize(
    "message_type,page_title", [
        ('email', 'Emails'),
        ('sms', 'Text messages')
    ]
)
@pytest.mark.parametrize(
    "status_argument, expected_api_call", [
        (
            '',
            ['created', 'sending', 'delivered', 'failed', 'temporary-failure', 'permanent-failure', 'technical-failure']
        ),
        (
            'sending',
            ['sending', 'created']
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
@pytest.mark.parametrize(
    "page_argument, expected_page_argument", [
        (1, 1),
        (22, 22),
        (None, 1)
    ]
)
def test_can_show_notifications(
    app_,
    service_one,
    active_user_with_permissions,
    mock_get_notifications,
    mock_get_detailed_service,
    mocker,
    message_type,
    page_title,
    status_argument,
    expected_api_call,
    page_argument,
    expected_page_argument
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            response = client.get(url_for(
                'main.view_notifications',
                service_id=service_one['id'],
                message_type=message_type,
                status=status_argument,
                page=page_argument))
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

        path_to_json = page.find("div", {'data-key': 'notifications'})['data-resource']

        url = urlparse(path_to_json)
        assert url.path == '/services/{}/notifications/{}.json'.format(service_one['id'], message_type)
        query_dict = parse_qs(url.query)
        if status_argument:
            assert query_dict['status'] == [status_argument]
        if expected_page_argument:
            assert query_dict['page'] == [str(expected_page_argument)]

        mock_get_notifications.assert_called_with(
            limit_days=7,
            page=expected_page_argument,
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

        json_response = client.get(url_for(
            'main.get_notifications_as_json',
            service_id=service_one['id'],
            message_type=message_type,
            status=status_argument
        ))
        json_content = json.loads(json_response.get_data(as_text=True))
        assert json_content.keys() == {'counts', 'notifications'}


def test_should_show_notifications_for_a_service_with_next_previous(
    app_,
    service_one,
    active_user_with_permissions,
    mock_get_notifications_with_previous_next,
    mock_get_detailed_service,
    mocker
):
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
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        next_page_link = page.find('a', {'rel': 'next'})
        prev_page_link = page.find('a', {'rel': 'previous'})
        assert (
            url_for('main.view_notifications', service_id=service_one['id'], message_type='sms', page=3) in
            next_page_link['href']
        )
        assert 'Next page' in next_page_link.text.strip()
        assert 'page 3' in next_page_link.text.strip()
        assert (
            url_for('main.view_notifications', service_id=service_one['id'], message_type='sms', page=1) in
            prev_page_link['href']
        )
        assert 'Previous page' in prev_page_link.text.strip()
        assert 'page 1' in prev_page_link.text.strip()


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
        assert 'sample template - 1 January at 11:09am.csv"' in response.headers['Content-Disposition']


@pytest.mark.parametrize(
    "job_created_at, expected_message", [
        ("2016-01-10 11:09:00.000000+00:00", "Data available for 7 days"),
        ("2016-01-04 11:09:00.000000+00:00", "Data available for 1 day"),
        ("2016-01-03 11:09:00.000000+00:00", "Data available for 11 hours"),
        ("2016-01-02 23:59:59.000000+00:00", "Data no longer available")
    ]
)
@freeze_time("2016-01-10 12:00:00.000000")
def test_time_left(job_created_at, expected_message):
    assert get_time_left(job_created_at) == expected_message


STATISTICS = {
    'sms': {
        'requested': 6,
        'failed': 2,
        'delivered': 1
    }
}


def test_get_status_filters_calculates_stats(app_):
    with app_.test_request_context():
        ret = get_status_filters({'id': 'foo'}, 'sms', STATISTICS)

    assert {label: count for label, _option, _link, count in ret} == {
        'total': 6,
        'sending': 3,
        'failed': 2,
        'delivered': 1
    }


def test_get_status_filters_in_right_order(app_):
    with app_.test_request_context():
        ret = get_status_filters({'id': 'foo'}, 'sms', STATISTICS)

    assert [label for label, _option, _link, _count in ret] == [
        'total', 'sending', 'delivered', 'failed'
    ]


def test_get_status_filters_constructs_links(app_):
    with app_.test_request_context():
        ret = get_status_filters({'id': 'foo'}, 'sms', STATISTICS)

    link = ret[0][2]
    assert link == '/services/foo/notifications/sms?status={}'.format(quote('sending,delivered,failed'))


def test_html_contains_notification_id(
        client,
        service_one,
        active_user_with_permissions,
        mock_get_notifications,
        mock_get_detailed_service,
        mocker
):
    client.login(active_user_with_permissions, mocker, service_one)
    response = client.get(url_for(
        'main.view_notifications',
        service_id=service_one['id'],
        message_type='sms',
        status='')
    )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    notifications = page.tbody.find_all('tr')
    for tr in notifications:
        assert uuid.UUID(tr.attrs['id'])
