import json
import uuid

import pytest
from flask import url_for
from freezegun import freeze_time

from app.main.views.jobs import get_time_left
from tests import job_json, notification_json, sample_uuid
from tests.conftest import (
    SERVICE_ONE_ID,
    active_caseworking_user,
    active_user_with_permissions,
    mock_get_notifications,
    mock_get_service_letter_template,
    normalize_spaces,
)


@pytest.mark.parametrize('user, expected_rows', [
    (active_user_with_permissions, (
        (
            'File Sending Delivered Failed'
        ),
        (
            'export 1/1/2016.xls '
            'Sent 12 December at 12:12pm 1 0 0'
        ),
        (
            'all email addresses.xlsx '
            'Sent 12 December at 12:12pm 1 0 0'
        ),
        (
            'applicants.ods '
            'Sent 12 December at 12:12pm 1 0 0'
        ),
        (
            'thisisatest.csv '
            'Sent 12 December at 12:12pm 1 0 0'
        ),
    )),
    (active_caseworking_user, (
        (
            'File Messages to be sent'
        ),
        (
            'send_me_later.csv '
            'Sending 1 January at 11:09am 1'
        ),
        (
            'even_later.csv '
            'Sending 1 January at 11:09pm 1'
        ),
        (
            'File Sending Delivered Failed'
        ),
        (
            'export 1/1/2016.xls '
            'Sent 12 December at 12:12pm 1 0 0'
        ),
        (
            'all email addresses.xlsx '
            'Sent 12 December at 12:12pm 1 0 0'
        ),
        (
            'applicants.ods '
            'Sent 12 December at 12:12pm 1 0 0'
        ),
        (
            'thisisatest.csv '
            'Sent 12 December at 12:12pm 1 0 0'
        ),
    )),
])
@freeze_time("2012-12-12 12:12")
def test_jobs_page_shows_scheduled_jobs_if_user_doesnt_have_dashboard(
    client_request,
    service_one,
    active_user_with_permissions,
    mock_get_jobs,
    fake_uuid,
    user,
    expected_rows,
):
    client_request.login(user(fake_uuid))
    page = client_request.get('main.view_jobs', service_id=service_one['id'])

    for index, row in enumerate(expected_rows):
        assert normalize_spaces(page.select('tr')[index].text) == row


@pytest.mark.parametrize('user', [
    active_user_with_permissions,
    active_caseworking_user,
])
def test_get_jobs_shows_page_links(
    client_request,
    active_user_with_permissions,
    mock_get_jobs,
    user,
    fake_uuid,
):
    client_request.login(user(fake_uuid))
    page = client_request.get('main.view_jobs', service_id=SERVICE_ONE_ID)

    assert 'Next page' in page.find('li', {'class': 'next-page'}).text
    assert 'Previous page' in page.find('li', {'class': 'previous-page'}).text


@pytest.mark.parametrize('user', [
    active_user_with_permissions,
    active_caseworking_user,
])
@freeze_time("2012-12-12 12:12")
def test_jobs_page_doesnt_show_scheduled_on_page_2(
    client_request,
    service_one,
    active_user_with_permissions,
    mock_get_jobs,
    fake_uuid,
    user,
):
    client_request.login(user(fake_uuid))
    page = client_request.get('main.view_jobs', service_id=service_one['id'], page=2)

    for index, row in enumerate((
        (
            'File Sending Delivered Failed'
        ),
        (
            'export 1/1/2016.xls '
            'Sent 12 December at 12:12pm 1 0 0'
        ),
        (
            'all email addresses.xlsx '
            'Sent 12 December at 12:12pm 1 0 0'
        ),
        (
            'applicants.ods '
            'Sent 12 December at 12:12pm 1 0 0'
        ),
        (
            'thisisatest.csv '
            'Sent 12 December at 12:12pm 1 0 0'
        ),
    )):
        assert normalize_spaces(page.select('tr')[index].text) == row


@pytest.mark.parametrize('user', [
    active_user_with_permissions,
    active_caseworking_user,
])
@pytest.mark.parametrize(
    "status_argument, expected_api_call", [
        (
            '',
            [
                'created', 'pending', 'sending', 'pending-virus-check',
                'delivered', 'sent', 'returned-letter',
                'failed', 'temporary-failure', 'permanent-failure', 'technical-failure',
                'virus-scan-failed', 'validation-failed'
            ]
        ),
        (
            'sending',
            ['sending', 'created', 'pending', 'pending-virus-check']
        ),
        (
            'delivered',
            ['delivered', 'sent', 'returned-letter']
        ),
        (
            'failed',
            [
                'failed', 'temporary-failure', 'permanent-failure', 'technical-failure', 'virus-scan-failed',
                'validation-failed'
            ]
        )
    ]
)
@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_page_for_one_job(
    client_request,
    active_user_with_permissions,
    mock_get_service_template,
    mock_get_job,
    mocker,
    mock_get_notifications,
    mock_get_service_data_retention,
    fake_uuid,
    status_argument,
    expected_api_call,
    user,
):

    page = client_request.get(
        'main.view_job',
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        status=status_argument
    )

    assert page.h1.text.strip() == 'thisisatest.csv'
    assert ' '.join(page.find('tbody').find('tr').text.split()) == (
        '07123456789 template content Delivered 1 January at 11:10am'
    )
    assert page.find('div', {'data-key': 'notifications'})['data-resource'] == url_for(
        'main.view_job_updates',
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        status=status_argument,
    )
    csv_link = page.select_one('a[download]')
    assert csv_link['href'] == url_for(
        'main.view_job_csv',
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        status=status_argument
    )
    assert csv_link.text == 'Download this report'
    assert page.find('span', {'id': 'time-left'}).text == 'Data available for 7 days'

    assert normalize_spaces(page.select_one('tbody tr').text) == normalize_spaces(
        '07123456789 '
        'template content '
        'Delivered 1 January at 11:10am'
    )
    assert page.select_one('tbody tr a')['href'] == url_for(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=sample_uuid(),
        from_job=fake_uuid,
    )

    mock_get_notifications.assert_called_with(
        SERVICE_ONE_ID,
        fake_uuid,
        status=expected_api_call
    )


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_page_for_one_job_with_flexible_data_retention(
    client_request,
    active_user_with_permissions,
    mock_get_service_template,
    mock_get_job,
    mocker,
    mock_get_notifications,
    mock_get_service_data_retention,
    fake_uuid,
):

    mock_get_service_data_retention.side_effect = [[{"days_of_retention": 10, "notification_type": "sms"}]]
    page = client_request.get(
        'main.view_job',
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        status='delivered'
    )

    assert page.find('span', {'id': 'time-left'}).text == 'Data available for 10 days'
    assert "Cancel sending these letters" not in page


def test_get_jobs_should_tell_user_if_more_than_one_page(
    client_request,
    fake_uuid,
    service_one,
    mock_get_job,
    mock_get_service_template,
    mock_get_notifications_with_previous_next,
    mock_get_service_data_retention,
):
    page = client_request.get(
        'main.view_job',
        service_id=service_one['id'],
        job_id=fake_uuid,
        status='',
    )
    assert page.find('p', {'class': 'table-show-more-link'}).text.strip() == 'Only showing the first 50 rows'


def test_should_show_job_in_progress(
    client_request,
    service_one,
    active_user_with_permissions,
    mock_get_service_template,
    mock_get_job_in_progress,
    mocker,
    mock_get_notifications,
    mock_get_service_data_retention,
    fake_uuid,
):
    page = client_request.get(
        'main.view_job',
        service_id=service_one['id'],
        job_id=fake_uuid,
    )
    assert page.find('p', {'class': 'hint'}).text.strip() == 'Report is 50% complete…'


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_letter_job(
    client_request,
    mock_get_service_letter_template,
    mock_get_job,
    mock_get_service_data_retention,
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
        'Sent by Test User on 1 January at 11:09am Printing starts today at 5:30pm'
    )
    assert page.select('.banner-default-with-tick') == []
    assert normalize_spaces(page.select('tbody tr')[0].text) == (
        '1 Example Street template subject 1 January at 11:09am'
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
            'returned-letter',
            'failed',
            'temporary-failure',
            'permanent-failure',
            'technical-failure',
            'virus-scan-failed',
            'validation-failed'
        ],
    )


@freeze_time("2016-01-01 11:09:00")
def test_should_show_letter_job_with_banner_after_sending_before_1730(
    client_request,
    mock_get_service_letter_template,
    mock_get_job,
    mock_get_notifications,
    mock_get_service_data_retention,
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
        'Your letter has been sent. Printing starts today at 5:30pm.'
    )


@freeze_time("2016-01-01 11:09:00")
def test_should_show_letter_job_with_banner_when_there_are_multiple_CSV_rows(
    client_request,
    mock_get_service_letter_template,
    mock_get_job_in_progress,
    mock_get_notifications,
    mock_get_service_data_retention,
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
        'Your letters have been sent. Printing starts today at 5:30pm.'
    )


@freeze_time("2016-01-01 18:09:00")
def test_should_show_letter_job_with_banner_after_sending_after_1730(
    client_request,
    mock_get_service_letter_template,
    mock_get_job,
    mock_get_notifications,
    mock_get_service_data_retention,
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
        'Your letter has been sent. Printing starts tomorrow at 5:30pm.'
    )


@freeze_time("2016-01-01T00:00:00.061258")
def test_should_show_scheduled_job(
    client_request,
    mock_get_service_template,
    mock_get_scheduled_job,
    mock_get_service_data_retention,
    mock_get_notifications,
    fake_uuid,
):
    page = client_request.get(
        'main.view_job',
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
    )

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
    client_request,
    fake_uuid,
    mocker,
):
    mock_cancel = mocker.patch('app.main.jobs.job_api_client.cancel_job')
    client_request.post(
        'main.cancel_job',
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_dashboard',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )

    mock_cancel.assert_called_once_with(SERVICE_ONE_ID, fake_uuid)


def test_should_not_show_cancelled_job(
    client_request,
    active_user_with_permissions,
    mock_get_cancelled_job,
    fake_uuid,
):
    client_request.get(
        'main.view_job',
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
        _expected_status=404,
    )


def test_should_cancel_letter_job(
    client_request,
    mocker,
    active_user_with_permissions
):
    job_id = uuid.uuid4()
    job = job_json(
        SERVICE_ONE_ID,
        active_user_with_permissions,
        job_id=job_id,
        created_at="2019-06-20T15:30:00.000001+00:00",
        job_status="finished"
    )
    mocker.patch('app.job_api_client.get_job', side_effect=[{"data": job}])
    notifications_json = notification_json(SERVICE_ONE_ID, job=job, status="created", template_type="letter")
    mocker.patch('app.job_api_client.get_job', side_effect=[{"data": job}])
    mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=[notifications_json]
    )
    mock_cancel = mocker.patch('app.main.jobs.job_api_client.cancel_letter_job', return_value=5)
    client_request.post(
        'main.cancel_letter_job',
        service_id=SERVICE_ONE_ID,
        job_id=job_id,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_dashboard',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )
    mock_cancel.assert_called_once_with(SERVICE_ONE_ID, job_id)


@freeze_time("2019-06-20 17:30:00.000001")
@pytest.mark.parametrize("job_created_at, expected_fragment", [
    ("2019-06-20T15:30:00.000001+00:00", "today"),
    ("2019-06-19T15:30:00.000001+00:00", "yesterday"),
    ("2019-06-18T15:30:00.000001+00:00", "on 18 June"),
])
def test_should_not_show_cancel_link_for_letter_job_if_too_late(
    client_request,
    mocker,
    mock_get_service_letter_template,
    mock_get_service_data_retention,
    active_user_with_permissions,
    job_created_at,
    expected_fragment,
):
    job_id = uuid.uuid4()
    job = job_json(
        SERVICE_ONE_ID, active_user_with_permissions, job_id=job_id, created_at=job_created_at
    )
    notifications_json = notification_json(SERVICE_ONE_ID, job=job, status="created", template_type="letter")
    mocker.patch('app.job_api_client.get_job', side_effect=[{"data": job}])
    mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=[notifications_json]
    )

    page = client_request.get(
        'main.view_job',
        service_id=SERVICE_ONE_ID,
        job_id=str(job_id)
    )

    assert "Cancel sending these letters" not in page
    assert page.find('p', {'id': 'printing-info'}).text.strip() == "Printed {} at 5:30pm".format(expected_fragment)


@freeze_time("2019-06-20 15:32:00.000001")
@pytest.mark.parametrize(" job_status", [
    "finished", "in progress"
])
def test_should_show_cancel_link_for_letter_job(
    client_request,
    mocker,
    mock_get_service_letter_template,
    mock_get_service_data_retention,
    active_user_with_permissions,
    job_status,
):
    job_id = uuid.uuid4()
    job = job_json(
        SERVICE_ONE_ID,
        active_user_with_permissions,
        job_id=job_id,
        created_at="2019-06-20T15:30:00.000001+00:00",
        job_status=job_status
    )
    notifications_json = notification_json(SERVICE_ONE_ID, job=job, status="created", template_type="letter")
    mocker.patch('app.job_api_client.get_job', side_effect=[{"data": job}])
    mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=[notifications_json]
    )

    page = client_request.get(
        'main.view_job',
        service_id=SERVICE_ONE_ID,
        job_id=str(job_id)
    )

    assert page.find('a', text='Cancel sending these letters').attrs["href"] == url_for(
        "main.cancel_letter_job", service_id=SERVICE_ONE_ID, job_id=job_id
    )
    assert page.find('p', {'id': 'printing-info'}).text.strip() == "Printing starts today at 5:30pm"


@freeze_time("2019-06-20 15:31:00.000001")
@pytest.mark.parametrize('job_status,number_of_processed_notifications', [['in progress', 2], ['finished', 1]])
def test_dont_cancel_letter_job_when_to_early_to_cancel(
    client_request,
    mocker,
    mock_get_service_letter_template,
    mock_get_service_data_retention,
    active_user_with_permissions,
    job_status,
    number_of_processed_notifications,
):
    job_id = uuid.uuid4()
    job = job_json(
        SERVICE_ONE_ID,
        active_user_with_permissions,
        job_id=job_id,
        created_at="2019-06-20T15:30:00.000001+00:00",
        job_status=job_status,
        notification_count=2
    )
    mocker.patch('app.job_api_client.get_job', side_effect=[{"data": job}, {"data": job}])

    notifications_json = notification_json(
        SERVICE_ONE_ID, job=job, status="created", template_type="letter", rows=number_of_processed_notifications
    )
    mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=[notifications_json, notifications_json]
    )

    mock_cancel = mocker.patch('app.main.jobs.job_api_client.cancel_letter_job')
    page = client_request.post(
        'main.cancel_letter_job',
        service_id=SERVICE_ONE_ID,
        job_id=str(job_id),
        _expected_status=200,
    )
    mock_cancel.assert_not_called()
    flash_message = normalize_spaces(page.find('div', class_='banner-dangerous').text)

    assert 'We are still processing these letters, please try again in a minute.' in flash_message


@freeze_time("2016-01-01 00:00:00.000001")
def test_should_show_updates_for_one_job_as_json(
    logged_in_client,
    service_one,
    active_user_with_permissions,
    mock_get_notifications,
    mock_get_service_template,
    mock_get_job,
    mock_get_service_data_retention,
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
        ("2016-01-03 11:09:00.000000+00:00", "Data available for 12 hours"),
        ("2016-01-02 23:59:59.000000+00:00", "Data no longer available")
    ]
)
@freeze_time("2016-01-10 12:00:00.000000")
def test_time_left(job_created_at, expected_message):
    assert get_time_left(job_created_at) == expected_message


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_letter_job_with_first_class_if_notifications_are_first_class(
    client_request,
    mock_get_service_letter_template,
    mock_get_job,
    mock_get_service_data_retention,
    fake_uuid,
    active_user_with_permissions,
    mocker,
):
    mock_get_notifications(
        mocker,
        active_user_with_permissions,
        diff_template_type='letter',
        postage='first'
    )

    page = client_request.get(
        'main.view_job',
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
    )

    assert normalize_spaces(page.select('.keyline-block')[1].text) == '5 January Estimated delivery date'


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_letter_job_with_first_class_if_no_notifications(
    client_request,
    service_one,
    mock_get_job,
    fake_uuid,
    mock_get_notifications_with_no_notifications,
    mock_get_service_data_retention,
    mocker
):

    mock_get_service_letter_template(mocker, postage="first")

    page = client_request.get(
        'main.view_job',
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
    )

    assert normalize_spaces(page.select('.keyline-block')[1].text) == '5 January Estimated delivery date'
