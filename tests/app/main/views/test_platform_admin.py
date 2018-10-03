import datetime
import re
import uuid
from functools import partial
from unittest.mock import ANY

import pytest
import requests_mock
from bs4 import BeautifulSoup
from flask import current_app, url_for
from freezegun import freeze_time

from app.main.views.platform_admin import (
    create_global_stats,
    format_stats_by_service,
    get_tech_failure_status_box_data,
    is_over_threshold,
    sum_service_usage,
)
from tests import service_json
from tests.conftest import mock_get_user, normalize_spaces


@pytest.mark.parametrize('endpoint', [
    'main.platform_admin',
    'main.live_services',
    'main.trial_services',
])
def test_should_redirect_if_not_logged_in(
    client,
    endpoint
):
    response = client.get(url_for(endpoint))
    assert response.status_code == 302
    assert response.location == url_for('main.sign_in', next=url_for(endpoint), _external=True)


@pytest.mark.parametrize('endpoint', [
    'main.platform_admin',
    'main.live_services',
    'main.trial_services',
])
def test_should_403_if_not_platform_admin(
    client,
    active_user_with_permissions,
    mocker,
    endpoint,
):
    mock_get_user(mocker, user=active_user_with_permissions)
    client.login(active_user_with_permissions)
    response = client.get(url_for(endpoint))

    assert response.status_code == 403


@pytest.mark.parametrize('endpoint, restricted, research_mode, displayed', [
    ('main.trial_services', True, False, ''),
    ('main.live_services', False, False, 'Live'),
    ('main.live_services', False, True, 'research mode'),
    ('main.trial_services', True, True, 'research mode')
])
def test_should_show_research_and_restricted_mode(
    endpoint,
    restricted,
    research_mode,
    displayed,
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    fake_uuid,
):
    services = [service_json(fake_uuid, 'My Service', [], restricted=restricted, research_mode=research_mode)]
    services[0]['statistics'] = create_stats()

    mock_get_detailed_services.return_value = {'data': services}
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for(endpoint))

    assert response.status_code == 200
    mock_get_detailed_services.assert_called_once_with({'detailed': True,
                                                        'include_from_test_key': True,
                                                        'only_active': False})
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    # get first column in second row, which contains flags as text.
    table_body = page.find_all('table')[0].find_all('tbody')[0]
    service_mode = table_body.find_all('tbody')[0].find_all('tr')[1].find_all('td')[0].text.strip()
    assert service_mode == displayed


@pytest.mark.parametrize('endpoint, expected_services_shown', [
    ('main.live_services', 1),
    ('main.trial_services', 1),
])
def test_should_render_platform_admin_page(
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    endpoint,
    expected_services_shown
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for(endpoint))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert len(page.select('tbody tr')) == expected_services_shown * 3  # one row for SMS, one for email, one for letter
    mock_get_detailed_services.assert_called_once_with({'detailed': True,
                                                        'include_from_test_key': True,
                                                        'only_active': False})


@pytest.mark.parametrize('endpoint', [
    'main.live_services',
    'main.trial_services',
])
@pytest.mark.parametrize('partial_url_for, inc', [
    (partial(url_for), True),
    (partial(url_for, include_from_test_key='y', start_date='', end_date=''), True),
    (partial(url_for, start_date='', end_date=''), False),
])
def test_live_trial_services_toggle_including_from_test_key(
    partial_url_for,
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    endpoint,
    inc
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(partial_url_for(endpoint))

    assert response.status_code == 200
    mock_get_detailed_services.assert_called_once_with({
        'detailed': True,
        'only_active': False,
        'include_from_test_key': inc,
    })


@pytest.mark.parametrize('endpoint', [
    'main.live_services',
    'main.trial_services'
])
def test_live_trial_services_with_date_filter(
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    endpoint
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for(endpoint, start_date='2016-12-20', end_date='2016-12-28'))

    assert response.status_code == 200
    resp_data = response.get_data(as_text=True)
    assert 'Platform admin' in resp_data
    mock_get_detailed_services.assert_called_once_with({
        'include_from_test_key': False,
        'end_date': datetime.date(2016, 12, 28),
        'start_date': datetime.date(2016, 12, 20),
        'detailed': True,
        'only_active': False,
    })


@pytest.mark.parametrize('endpoint, expected_big_numbers', [
    (
        'main.live_services', (
            '55 emails sent 5 failed – 5.0%',
            '110 text messages sent 10 failed – 5.0%',
            '15 letters sent 3 failed – 20.0%'
        ),
    ),
    (
        'main.trial_services', (
            '6 emails sent 1 failed – 10.0%',
            '11 text messages sent 1 failed – 5.0%',
            '30 letters sent 10 failed – 33.3%'
        ),
    ),
])
def test_should_show_total_on_live_trial_services_pages(
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    endpoint,
    fake_uuid,
    expected_big_numbers,
):
    services = [
        service_json(fake_uuid, 'My Service 1', [], restricted=False),
        service_json(fake_uuid, 'My Service 2', [], restricted=True),
    ]
    services[0]['statistics'] = create_stats(
        emails_requested=100,
        emails_delivered=50,
        emails_failed=5,
        sms_requested=200,
        sms_delivered=100,
        sms_failed=10,
        letters_requested=15,
        letters_delivered=12,
        letters_failed=3
    )

    services[1]['statistics'] = create_stats(
        emails_requested=10,
        emails_delivered=5,
        emails_failed=1,
        sms_requested=20,
        sms_delivered=10,
        sms_failed=1,
        letters_requested=30,
        letters_delivered=20,
        letters_failed=10
    )

    mock_get_detailed_services.return_value = {'data': services}

    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for(endpoint))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert (
        normalize_spaces(page.select('.big-number-with-status')[0].text),
        normalize_spaces(page.select('.big-number-with-status')[1].text),
        normalize_spaces(page.select('.big-number-with-status')[2].text),
    ) == expected_big_numbers


def test_create_global_stats_sets_failure_rates(fake_uuid):
    services = [
        service_json(fake_uuid, 'a', []),
        service_json(fake_uuid, 'b', [])
    ]
    services[0]['statistics'] = create_stats(
        emails_requested=1,
        emails_delivered=1,
        emails_failed=0,
    )
    services[1]['statistics'] = create_stats(
        emails_requested=2,
        emails_delivered=1,
        emails_failed=1,
    )

    stats = create_global_stats(services)
    assert stats == {
        'email': {
            'delivered': 2,
            'failed': 1,
            'requested': 3,
            'failure_rate': '33.3'
        },
        'sms': {
            'delivered': 0,
            'failed': 0,
            'requested': 0,
            'failure_rate': '0'
        },
        'letter': {
            'delivered': 0,
            'failed': 0,
            'requested': 0,
            'failure_rate': '0'
        }
    }


def create_stats(
    emails_requested=0,
    emails_delivered=0,
    emails_failed=0,
    sms_requested=0,
    sms_delivered=0,
    sms_failed=0,
    letters_requested=0,
    letters_delivered=0,
    letters_failed=0
):
    return {
        'sms': {
            'requested': sms_requested,
            'delivered': sms_delivered,
            'failed': sms_failed,
        },
        'email': {
            'requested': emails_requested,
            'delivered': emails_delivered,
            'failed': emails_failed,
        },
        'letter': {
            'requested': letters_requested,
            'delivered': letters_delivered,
            'failed': letters_failed,
        },
    }


def test_format_stats_by_service_returns_correct_values(fake_uuid):
    services = [service_json(fake_uuid, 'a', [])]
    services[0]['statistics'] = create_stats(
        emails_requested=10,
        emails_delivered=3,
        emails_failed=5,
        sms_requested=50,
        sms_delivered=7,
        sms_failed=11,
        letters_requested=40,
        letters_delivered=20,
        letters_failed=7
    )

    ret = list(format_stats_by_service(services))
    assert len(ret) == 1

    assert ret[0]['stats']['email']['sending'] == 2
    assert ret[0]['stats']['email']['delivered'] == 3
    assert ret[0]['stats']['email']['failed'] == 5

    assert ret[0]['stats']['sms']['sending'] == 32
    assert ret[0]['stats']['sms']['delivered'] == 7
    assert ret[0]['stats']['sms']['failed'] == 11

    assert ret[0]['stats']['letter']['sending'] == 13
    assert ret[0]['stats']['letter']['delivered'] == 20
    assert ret[0]['stats']['letter']['failed'] == 7


@pytest.mark.parametrize('endpoint, restricted, research_mode', [
    ('main.trial_services', True, False),
    ('main.live_services', False, False)
])
def test_should_show_email_and_sms_stats_for_all_service_types(
    endpoint,
    restricted,
    research_mode,
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    fake_uuid,
):
    services = [service_json(fake_uuid, 'My Service', [], restricted=restricted, research_mode=research_mode)]
    services[0]['statistics'] = create_stats(
        emails_requested=10,
        emails_delivered=3,
        emails_failed=5,
        sms_requested=50,
        sms_delivered=7,
        sms_failed=11
    )

    mock_get_detailed_services.return_value = {'data': services}
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for(endpoint))

    assert response.status_code == 200
    mock_get_detailed_services.assert_called_once_with({'detailed': True,
                                                        'include_from_test_key': True,
                                                        'only_active': ANY})
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    table_body = page.find_all('table')[0].find_all('tbody')[0]
    service_row_group = table_body.find_all('tbody')[0].find_all('tr')
    email_stats = service_row_group[0].find_all('div', class_='big-number-number')
    sms_stats = service_row_group[1].find_all('div', class_='big-number-number')
    email_sending, email_delivered, email_failed = [int(x.text.strip()) for x in email_stats]
    sms_sending, sms_delivered, sms_failed = [int(x.text.strip()) for x in sms_stats]

    assert email_sending == 2
    assert email_delivered == 3
    assert email_failed == 5
    assert sms_sending == 32
    assert sms_delivered == 7
    assert sms_failed == 11


@pytest.mark.parametrize('endpoint, restricted', [
    ('main.live_services', False),
    ('main.trial_services', True)
], ids=['live', 'trial'])
def test_should_show_archived_services_last(
    endpoint,
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    restricted,
):
    services = [
        service_json(name='C', restricted=restricted, active=False, created_at='2002-02-02 12:00:00'),
        service_json(name='B', restricted=restricted, active=True, created_at='2001-01-01 12:00:00'),
        service_json(name='A', restricted=restricted, active=True, created_at='2003-03-03 12:00:00'),
    ]
    services[0]['statistics'] = create_stats()
    services[1]['statistics'] = create_stats()
    services[2]['statistics'] = create_stats()

    mock_get_detailed_services.return_value = {'data': services}
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for(endpoint))

    assert response.status_code == 200
    mock_get_detailed_services.assert_called_once_with({'detailed': True,
                                                        'include_from_test_key': True,
                                                        'only_active': ANY})
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    table_body = page.find_all('table')[0].find_all('tbody')[0]
    services = [service.tr for service in table_body.find_all('tbody')]
    assert len(services) == 3
    assert services[0].td.text.strip() == 'A'
    assert services[1].td.text.strip() == 'B'
    assert services[2].td.text.strip() == 'C'


@pytest.mark.parametrize('research_mode', (True, False))
def test_shows_archived_label_instead_of_live_or_research_mode_label(
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    research_mode,
):
    services = [
        service_json(restricted=False, research_mode=research_mode, active=False)
    ]
    services[0]['statistics'] = create_stats()

    mock_get_detailed_services.return_value = {'data': services}
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for('main.live_services'))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    table_body = page.find_all('table')[0].find_all('tbody')[0]
    service_mode = table_body.find_all('tbody')[0].find_all('tr')[1].td.text.strip()
    # get second column, which contains flags as text.
    assert service_mode == 'archived'


@pytest.mark.parametrize('endpoint, restricted, research_mode', [
    ('main.trial_services', True, False),
    ('main.live_services', False, False)
])
def test_should_order_services_by_usage_with_inactive_last(
    endpoint,
    restricted,
    research_mode,
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    fake_uuid,
):
    services = [
        service_json(fake_uuid, 'My Service 1', [], restricted=restricted, research_mode=research_mode),
        service_json(fake_uuid, 'My Service 2', [], restricted=restricted, research_mode=research_mode),
        service_json(fake_uuid, 'My Service 3', [], restricted=restricted, research_mode=research_mode, active=False)
    ]
    services[0]['statistics'] = create_stats(
        emails_requested=100,
        emails_delivered=25,
        emails_failed=25,
        sms_requested=100,
        sms_delivered=25,
        sms_failed=25
    )

    services[1]['statistics'] = create_stats(
        emails_requested=200,
        emails_delivered=50,
        emails_failed=50,
        sms_requested=200,
        sms_delivered=50,
        sms_failed=50
    )

    services[2]['statistics'] = create_stats(
        emails_requested=200,
        emails_delivered=50,
        emails_failed=50,
        sms_requested=200,
        sms_delivered=50,
        sms_failed=50
    )

    mock_get_detailed_services.return_value = {'data': services}
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for(endpoint))

    assert response.status_code == 200
    mock_get_detailed_services.assert_called_once_with({'detailed': True,
                                                        'include_from_test_key': True,
                                                        'only_active': ANY})
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    table_body = page.find_all('table')[0].find_all('tbody')[0]
    services = [service.tr for service in table_body.find_all('tbody')]
    assert len(services) == 3
    assert services[0].td.text.strip() == 'My Service 2'
    assert services[1].td.text.strip() == 'My Service 1'
    assert services[2].td.text.strip() == 'My Service 3'


def test_sum_service_usage_is_sum_of_all_activity(fake_uuid):
    service = service_json(fake_uuid, 'My Service 1')
    service['statistics'] = create_stats(
        emails_requested=100,
        emails_delivered=25,
        emails_failed=25,
        sms_requested=100,
        sms_delivered=25,
        sms_failed=25
    )
    assert sum_service_usage(service) == 200


def test_sum_service_usage_with_zeros(fake_uuid):
    service = service_json(fake_uuid, 'My Service 1')
    service['statistics'] = create_stats(
        emails_requested=0,
        emails_delivered=0,
        emails_failed=25,
        sms_requested=0,
        sms_delivered=0,
        sms_failed=0
    )
    assert sum_service_usage(service) == 0


def test_platform_admin_list_complaints(
        client,
        platform_admin_user,
        mocker
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    complaint = {
        'id': str(uuid.uuid4()),
        'notification_id': str(uuid.uuid4()),
        'service_id': str(uuid.uuid4()),
        'service_name': 'Sample service',
        'ses_feedback_id': 'Some ses id',
        'complaint_type': 'abuse',
        'complaint_date': '2018-06-05T13:50:30.012354',
        'created_at': '2018-06-05T13:50:30.012354',
    }
    mock = mocker.patch('app.complaint_api_client.get_all_complaints',
                        return_value={'complaints': [complaint], 'links': {}})

    client.login(platform_admin_user)
    response = client.get(url_for('main.platform_admin_list_complaints'))

    assert response.status_code == 200
    resp_data = response.get_data(as_text=True)
    assert 'Email complaints' in resp_data
    assert mock.called


def test_should_show_complaints_with_next_previous(mocker, client, platform_admin_user, service_one, fake_uuid):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)

    api_response = {
        'complaints': [{'complaint_date': None,
                        'complaint_type': None,
                        'created_at': '2017-12-18T05:00:00.000000Z',
                        'id': fake_uuid,
                        'notification_id': fake_uuid,
                        'service_id': service_one['id'],
                        'service_name': service_one['name'],
                        'ses_feedback_id': 'None'}],
        'links': {'last': '/complaint?page=3', 'next': '/complaint?page=3', 'prev': '/complaint?page=1'}
    }

    mocker.patch('app.complaint_api_client.get_all_complaints', return_value=api_response)

    response = client.get(url_for('main.platform_admin_list_complaints', page=2))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    next_page_link = page.find('a', {'rel': 'next'})
    prev_page_link = page.find('a', {'rel': 'previous'})
    assert (url_for('main.platform_admin_list_complaints', page=3) in next_page_link['href'])
    assert 'Next page' in next_page_link.text.strip()
    assert 'page 3' in next_page_link.text.strip()
    assert (url_for('main.platform_admin_list_complaints', page=1) in prev_page_link['href'])
    assert 'Previous page' in prev_page_link.text.strip()
    assert 'page 1' in prev_page_link.text.strip()


def test_platform_admin_list_complaints_returns_404_with_invalid_page(mocker, client, platform_admin_user):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)

    mocker.patch('app.complaint_api_client.get_all_complaints', return_value={'complaints': [], 'links': {}})

    response = client.get(url_for('main.platform_admin_list_complaints', page='invalid'))

    assert response.status_code == 404


@pytest.mark.parametrize('number, total, threshold, result', [
    (0, 0, 0, False),
    (1, 1, 0, True),
    (2, 3, 66, True),
    (2, 3, 67, False),
])
def test_is_over_threshold(number, total, threshold, result):
    assert is_over_threshold(number, total, threshold) is result


def test_get_tech_failure_status_box_data_removes_percentage_data():
    stats = {
        'failures':
            {'permanent-failure': 0, 'technical-failure': 0, 'temporary-failure': 1, 'virus-scan-failed': 0},
        'test-key': 0,
        'total': 5589
    }
    tech_failure_data = get_tech_failure_status_box_data(stats)

    assert 'percentage' not in tech_failure_data


def test_platform_admin_with_start_and_end_dates_provided(mocker, logged_in_platform_admin_client):
    start_date = '2018-01-01'
    end_date = '2018-06-01'
    api_args = {'start_date': datetime.date(2018, 1, 1), 'end_date': datetime.date(2018, 6, 1)}

    mocker.patch('app.main.views.platform_admin.make_columns')
    aggregate_stats_mock = mocker.patch(
        'app.main.views.platform_admin.platform_stats_api_client.get_aggregate_platform_stats')
    complaint_count_mock = mocker.patch('app.main.views.platform_admin.complaint_api_client.get_complaint_count')

    logged_in_platform_admin_client.get(
        url_for('main.platform_admin', start_date=start_date, end_date=end_date)
    )

    aggregate_stats_mock.assert_called_with(api_args)
    complaint_count_mock.assert_called_with(api_args)


@freeze_time('2018-6-11')
def test_platform_admin_with_only_a_start_date_provided(mocker, logged_in_platform_admin_client):
    start_date = '2018-01-01'
    api_args = {'start_date': datetime.date(2018, 1, 1), 'end_date': datetime.datetime.utcnow().date()}

    mocker.patch('app.main.views.platform_admin.make_columns')
    aggregate_stats_mock = mocker.patch(
        'app.main.views.platform_admin.platform_stats_api_client.get_aggregate_platform_stats')
    complaint_count_mock = mocker.patch('app.main.views.platform_admin.complaint_api_client.get_complaint_count')

    logged_in_platform_admin_client.get(url_for('main.platform_admin', start_date=start_date))

    aggregate_stats_mock.assert_called_with(api_args)
    complaint_count_mock.assert_called_with(api_args)


def test_platform_admin_without_dates_provided(mocker, logged_in_platform_admin_client):
    api_args = {}

    mocker.patch('app.main.views.platform_admin.make_columns')
    aggregate_stats_mock = mocker.patch(
        'app.main.views.platform_admin.platform_stats_api_client.get_aggregate_platform_stats')
    complaint_count_mock = mocker.patch('app.main.views.platform_admin.complaint_api_client.get_complaint_count')

    logged_in_platform_admin_client.get(url_for('main.platform_admin'))

    aggregate_stats_mock.assert_called_with(api_args)
    complaint_count_mock.assert_called_with(api_args)


def test_platform_admin_displays_stats_in_right_boxes_and_with_correct_styling(
    mocker,
    logged_in_platform_admin_client,
):
    platform_stats = {
        'email': {'failures':
                  {'permanent-failure': 3, 'technical-failure': 0, 'temporary-failure': 0, 'virus-scan-failed': 0},
                  'test-key': 0,
                  'total': 145},
        'sms': {'failures':
                {'permanent-failure': 0, 'technical-failure': 1, 'temporary-failure': 0, 'virus-scan-failed': 0},
                'test-key': 5,
                'total': 168},
        'letter': {'failures':
                   {'permanent-failure': 0, 'technical-failure': 0, 'temporary-failure': 1, 'virus-scan-failed': 1},
                   'test-key': 0,
                   'total': 500}
    }
    mocker.patch('app.main.views.platform_admin.platform_stats_api_client.get_aggregate_platform_stats',
                 return_value=platform_stats)
    mocker.patch('app.main.views.platform_admin.complaint_api_client.get_complaint_count', return_value=15)

    response = logged_in_platform_admin_client.get(url_for('main.platform_admin'))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    # Email permanent failure status box - number is correct
    assert '3 permanent failures' in page.find_all('div', class_='column-third')[0].find(string=re.compile('permanent'))
    # Email complaints status box - link exists and number is correct
    assert page.find('a', string='15 complaints')
    # SMS total box - number is correct
    assert page.find_all('div', class_='big-number-number')[1].text.strip() == '168'
    # Test SMS box - number is correct
    assert '5' in page.find_all('div', class_='column-third')[4].text
    # SMS technical failure status box - number is correct and failure class is used
    assert '1 technical failures' in page.find_all('div', class_='column-third')[1].find(
        'div', class_='big-number-status-failing').text
    # Letter virus scan failure status box - number is correct and failure class is used
    assert '1 virus scan failures' in page.find_all('div', class_='column-third')[2].find(
        'div', class_='big-number-status-failing').text


def test_platform_admin_submit_returned_letters(mocker, client, platform_admin_user):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)

    mock_client = mocker.patch('app.letter_jobs_client.submit_returned_letters')

    response = client.post(
        url_for('main.platform_admin_returned_letters'),
        data={'references': ' NOTIFY000REF1 \n NOTIFY002REF2 '}
    )

    mock_client.assert_called_once_with(['REF1', 'REF2'])

    assert response.status_code == 302
    assert response.location == url_for('main.platform_admin_returned_letters', _external=True)


def test_platform_admin_submit_empty_returned_letters(mocker, client, platform_admin_user):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)

    mock_client = mocker.patch('app.letter_jobs_client.submit_returned_letters')

    response = client.post(
        url_for('main.platform_admin_returned_letters'),
        data={'references': '  \n  '}
    )

    assert not mock_client.called

    assert response.status_code == 200
    assert "Can’t be empty" in response.get_data(as_text=True)


def test_letter_validation_preview_renders_correctly(mocker, client, platform_admin_user):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for('main.platform_admin_letter_validation_preview'))
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('h1').text.strip() == "Letter Validation Preview"
    assert page.find_all('input', class_='file-upload-field')


@pytest.mark.parametrize("result,expected_class", [(True, 'banner-with-tick'), (False, "banner-dangerous")])
def test_letter_validation_preview_calls_template_preview_when_data_correct_and_displays_correct_message(
    mocker, client, platform_admin_user, result, expected_class
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    endpoint = '{}/precompiled/validate?include_preview=true'.format(current_app.config['TEMPLATE_PREVIEW_API_HOST'])
    mocker.patch('app.main.views.platform_admin.antivirus_client.scan', return_value=True)

    with requests_mock.mock() as rmock:
        rmock.request(
            "POST",
            endpoint,
            json={"pages": [], "message": "bazinga!", "result": result},
            status_code=200
        )
        with open('tests/test_pdf_files/multi_page_pdf.pdf', 'rb') as file:
            response = client.post(
                url_for('main.platform_admin_letter_validation_preview'),
                data={"file": file},
                content_type='multipart/form-data'
            )
        assert response.status_code == 200
        assert rmock.called
        assert rmock.request_history[0].url == endpoint

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('div', class_=expected_class).text.strip() == "bazinga!"


def test_letter_validation_preview_doesnt_call_template_preview_when_no_file(mocker, client, platform_admin_user):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    antivirus_scan = mocker.patch('app.main.views.platform_admin.antivirus_client.scan')
    validate_letter = mocker.patch('app.main.views.platform_admin.validate_letter')
    response = client.post(
        url_for('main.platform_admin_letter_validation_preview'),
        data={"file": ""},
        content_type='multipart/form-data'
    )
    assert response.status_code == 200
    antivirus_scan.assert_not_called()
    validate_letter.assert_not_called()

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('span', class_='error-message').text.strip() == "You need to upload a file to submit"


def test_letter_validation_preview_doesnt_call_template_preview_when_file_not_pdf(mocker, client, platform_admin_user):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    antivirus_scan = mocker.patch('app.main.views.platform_admin.antivirus_client.scan')
    validate_letter = mocker.patch('app.main.views.platform_admin.validate_letter')
    with open('tests/non_spreadsheet_files/actually_a_png.csv', 'rb') as file:
        response = client.post(
            url_for('main.platform_admin_letter_validation_preview'),
            data={"file": file},
            content_type='multipart/form-data'
        )
    assert response.status_code == 200
    antivirus_scan.assert_not_called()
    validate_letter.assert_not_called()
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('span', class_='error-message').text.strip() == "PDF documents only!"


def test_letter_validation_preview_doesnt_call_template_preview_when_file_doesnt_pass_virus_scan(
    mocker, client, platform_admin_user
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    antivirus_scan = mocker.patch('app.main.views.platform_admin.antivirus_client.scan', return_value=False)
    validate_letter = mocker.patch('app.main.views.platform_admin.validate_letter')

    with open('tests/test_pdf_files/multi_page_pdf.pdf', 'rb') as file:
        response = client.post(
            url_for('main.platform_admin_letter_validation_preview'),
            data={"file": file},
            content_type='multipart/form-data'
        )
    assert response.status_code == 400
    assert antivirus_scan.called is True
    validate_letter.assert_not_called()

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('div', class_='banner-dangerous').text.strip() == "Document didn't pass the virus scan"
