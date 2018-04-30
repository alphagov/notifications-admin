import json

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from freezegun import freeze_time

from app.main.views.jobs import get_time_left
from tests.conftest import (
    SERVICE_ONE_ID,
    mock_get_notifications,
    normalize_spaces,
)


def test_get_jobs_should_return_list_of_all_real_jobs(
    logged_in_client,
    service_one,
    active_user_with_permissions,
    mock_get_jobs,
    mocker,
):
    response = logged_in_client.get(url_for('main.view_jobs', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string == 'Uploaded files'
    jobs = [x.text for x in page.tbody.find_all('a', {'class': 'file-list-filename'})]
    assert len(jobs) == 4


def test_get_jobs_shows_page_links(
    logged_in_client,
    service_one,
    active_user_with_permissions,
    mock_get_jobs,
    mocker,
):
    response = logged_in_client.get(url_for('main.view_jobs', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Next page' in page.find('li', {'class': 'next-page'}).text
    assert 'Previous page' in page.find('li', {'class': 'previous-page'}).text


@pytest.mark.parametrize(
    "status_argument, expected_api_call", [
        (
            '',
            [
                'created', 'pending', 'sending', 'pending-virus-check',
                'delivered', 'sent',
                'failed', 'temporary-failure', 'permanent-failure', 'technical-failure', 'virus-scan-failed',
            ]
        ),
        (
            'sending',
            ['sending', 'created', 'pending', 'pending-virus-check']
        ),
        (
            'delivered',
            ['delivered', 'sent']
        ),
        (
            'failed',
            ['failed', 'temporary-failure', 'permanent-failure', 'technical-failure', 'virus-scan-failed']
        )
    ]
)
@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_page_for_one_job(
    logged_in_client,
    service_one,
    active_user_with_permissions,
    mock_get_service_template,
    mock_get_job,
    mocker,
    mock_get_notifications,
    fake_uuid,
    status_argument,
    expected_api_call,
):

    response = logged_in_client.get(url_for(
        'main.view_job',
        service_id=service_one['id'],
        job_id=fake_uuid,
        status=status_argument
    ))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.text.strip() == 'thisisatest.csv'
    assert ' '.join(page.find('tbody').find('tr').text.split()) == (
        '07123456789 template content Delivered 1 January at 11:10am'
    )
    assert page.find('div', {'data-key': 'notifications'})['data-resource'] == url_for(
        'main.view_job_updates',
        service_id=service_one['id'],
        job_id=fake_uuid,
        status=status_argument,
    )
    csv_link = page.select_one('a[download]')
    assert csv_link['href'] == url_for(
        'main.view_job_csv',
        service_id=service_one['id'],
        job_id=fake_uuid,
        status=status_argument
    )
    assert csv_link.text == 'Download this report'
    assert page.find('span', {'id': 'time-left'}).text == 'Data available for 7 days'
    mock_get_notifications.assert_called_with(
        service_one['id'],
        fake_uuid,
        status=expected_api_call
    )


def test_get_jobs_should_tell_user_if_more_than_one_page(
    logged_in_client,
    fake_uuid,
    service_one,
    mock_get_job,
    mock_get_service_template,
    mock_get_notifications_with_previous_next,
):
    response = logged_in_client.get(url_for(
        'main.view_job',
        service_id=service_one['id'],
        job_id=fake_uuid,
        status=''
    ))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('p', {'class': 'table-show-more-link'}).text.strip() == 'Only showing the first 50 rows'


def test_should_show_job_in_progress(
    logged_in_client,
    service_one,
    active_user_with_permissions,
    mock_get_service_template,
    mock_get_job_in_progress,
    mocker,
    mock_get_notifications,
    fake_uuid,
):

    response = logged_in_client.get(url_for(
        'main.view_job',
        service_id=service_one['id'],
        job_id=fake_uuid
    ))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('p', {'class': 'hint'}).text.strip() == 'Report is 50% complete…'


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_letter_job(
    client_request,
    mock_get_service_letter_template,
    mock_get_job,
    fake_uuid,
    active_user_with_permissions,
    mocker,
):

    get_notifications = mock_get_notifications(mocker, active_user_with_permissions, diff_template_type='letter')

    page = client_request.get(
        'main.view_job',
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
    )
    assert normalize_spaces(page.h1.text) == 'thisisatest.csv'
    assert normalize_spaces(page.select('p.bottom-gutter')[0].text) == (
        'Sent by Test User on 1 January at 11:09am'
    )
    assert page.select('.banner-default-with-tick') == []
    assert normalize_spaces(page.select('tbody tr')[0].text) == (
        '1 Example Street template content 1 January at 11:09am'
    )
    assert normalize_spaces(page.select('.keyline-block')[0].text) == (
        '1 Letter'
    )
    assert normalize_spaces(page.select('.keyline-block')[1].text) == (
        '6 January Estimated delivery date'
    )
    assert page.select('[download=download]') == []
    assert page.select('.hint') == []

    get_notifications.assert_called_with(
        SERVICE_ONE_ID,
        fake_uuid,
        status=[
            'created',
            'pending',
            'sending',
            'pending-virus-check',
            'delivered',
            'sent',
            'failed',
            'temporary-failure',
            'permanent-failure',
            'technical-failure',
            'virus-scan-failed',
        ],
    )


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_letter_job_with_banner_after_sending(
    client_request,
    mock_get_service_letter_template,
    mock_get_job,
    mock_get_notifications,
    fake_uuid,
):

    page = client_request.get(
        'main.view_job',
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        just_sent='yes',
    )

    assert page.select('p.bottom-gutter') == []
    assert normalize_spaces(page.select('.banner-default-with-tick')[0].text) == (
        'We’ve started printing your letters'
    )


@freeze_time("2016-01-01T00:00:00.061258")
def test_should_show_scheduled_job(
    logged_in_client,
    active_user_with_permissions,
    mock_get_service_template,
    mock_get_scheduled_job,
    mocker,
    mock_get_notifications,
    fake_uuid,
):
    response = logged_in_client.get(url_for(
        'main.view_job',
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid
    ))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert normalize_spaces(page.select('main p')[1].text) == (
        'Sending Two week reminder today at midnight'
    )
    assert page.select('main p a')[0]['href'] == url_for(
        'main.view_template_version',
        service_id=SERVICE_ONE_ID,
        template_id='5d729fbd-239c-44ab-b498-75a985f3198f',
        version=1,
    )
    assert page.select_one('button[type=submit]').text.strip() == 'Cancel sending'


def test_should_cancel_job(
    logged_in_client,
    service_one,
    fake_uuid,
    mocker,
):
    mock_cancel = mocker.patch('app.main.jobs.job_api_client.cancel_job')
    response = logged_in_client.post(url_for(
        'main.cancel_job',
        service_id=service_one['id'],
        job_id=fake_uuid
    ))

    mock_cancel.assert_called_once_with(service_one['id'], fake_uuid)
    assert response.status_code == 302
    assert response.location == url_for('main.service_dashboard', service_id=service_one['id'], _external=True)


def test_should_not_show_cancelled_job(
    logged_in_client,
    service_one,
    active_user_with_permissions,
    mock_get_cancelled_job,
    mocker,
    fake_uuid,
):
    response = logged_in_client.get(url_for(
        'main.view_job',
        service_id=service_one['id'],
        job_id=fake_uuid
    ))

    assert response.status_code == 404


@freeze_time("2016-01-01 00:00:00.000001")
def test_should_show_updates_for_one_job_as_json(
    logged_in_client,
    service_one,
    active_user_with_permissions,
    mock_get_notifications,
    mock_get_service_template,
    mock_get_job,
    mocker,
    fake_uuid,
):
    response = logged_in_client.get(url_for('main.view_job_updates', service_id=service_one['id'], job_id=fake_uuid))

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
    assert 'Sent by Test User on 1 January at midnight' in content['status']


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
