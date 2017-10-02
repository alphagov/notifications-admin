import datetime

from flask import url_for
import pytest
from bs4 import BeautifulSoup

from tests.conftest import mock_get_user, normalize_spaces
from tests import service_json

from app.main.views.platform_admin import format_stats_by_service, create_global_stats, sum_service_usage

from unittest.mock import ANY


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
                                                        'only_active': False,
                                                        'trial_mode_services': ANY})
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    # get first column in second row, which contains flags as text.
    table_body = page.find_all('table')[0].find_all('tbody')[0]
    service_mode = table_body.find_all('tbody')[0].find_all('tr')[1].find_all('td')[0].text.strip()
    assert service_mode == displayed


@pytest.mark.parametrize('endpoint, expected_services_shown, trial_mode_services', [
    ('main.live_services', 1, False),
    ('main.trial_services', 1, True),
])
def test_should_render_platform_admin_page(
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    endpoint,
    expected_services_shown,
    trial_mode_services,
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for(endpoint))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert len(page.select('tbody tr')) == expected_services_shown * 2  # one row for SMS, one for email
    mock_get_detailed_services.assert_called_once_with({'detailed': True,
                                                        'include_from_test_key': True,
                                                        'only_active': False,
                                                        'trial_mode_services': trial_mode_services})


@pytest.mark.parametrize('endpoint, trial_mode_services', [
    ('main.platform_admin', None),
    ('main.live_services', False),
    ('main.trial_services', True),
])
@pytest.mark.parametrize('include_from_test_key, inc', [
    ("Y", True),
    ("N", False)
])
def test_platform_admin_toggle_including_from_test_key(
    include_from_test_key,
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    endpoint,
    trial_mode_services,
    inc
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for(endpoint, include_from_test_key=include_from_test_key))

    assert response.status_code == 200
    mock_get_detailed_services.assert_called_once_with({'detailed': True,
                                                        'only_active': False,
                                                        'trial_mode_services': trial_mode_services,
                                                        'include_from_test_key': inc})


@pytest.mark.parametrize('endpoint, trial_mode_services', [
    ('main.platform_admin', None),
    ('main.live_services', False),
    ('main.trial_services', True)
])
def test_platform_admin_with_date_filter(
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    trial_mode_services,
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
        'trial_mode_services': trial_mode_services,
    })


@pytest.mark.parametrize('endpoint, expected_big_numbers', [
    (
        'main.platform_admin', (
            '61 emails sent 6 failed – 5.5%',
            '121 text messages sent 11 failed – 5.0%',
            '45 letters sent 13 failed – 28.9%'
        ),
    ),
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
def test_should_show_total_on_platform_admin_pages(
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


@pytest.mark.parametrize('endpoint, restricted, research_mode, trial_mode_services', [
    ('main.trial_services', True, False, True),
    ('main.live_services', False, False, False)
])
def test_should_show_email_and_sms_stats_for_all_service_types(
    endpoint,
    restricted,
    research_mode,
    trial_mode_services,
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
                                                        'trial_mode_services': trial_mode_services,
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


@pytest.mark.parametrize('endpoint, restricted, trial_mode_services', [
    ('main.live_services', False, False),
    ('main.trial_services', True, True)
], ids=['live', 'trial'])
def test_should_show_archived_services_last(
    endpoint,
    trial_mode_services,
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
                                                        'only_active': ANY,
                                                        'trial_mode_services': trial_mode_services})
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


def test_should_show_correct_sent_totals_for_platform_admin(
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    fake_uuid,
):
    services = [service_json(fake_uuid, 'My Service', [])]
    services[0]['statistics'] = create_stats(
        emails_requested=100,
        emails_delivered=20,
        emails_failed=40,
        sms_requested=100,
        sms_delivered=10,
        sms_failed=30,
        letters_requested=60,
        letters_delivered=40,
        letters_failed=5
    )

    mock_get_detailed_services.return_value = {'data': services}
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for('main.platform_admin'))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    totals = page.find_all('div', 'big-number-with-status')
    email_total = int(totals[0].find_all('div', 'big-number-number')[0].text.strip())
    sms_total = int(totals[1].find_all('div', 'big-number-number')[0].text.strip())
    letter_total = int(totals[2].find_all('div', 'big-number-number')[0].text.strip())

    assert email_total == 60
    assert sms_total == 40
    assert letter_total == 45


@pytest.mark.parametrize('endpoint, restricted, research_mode, trial_mode_services', [
    ('main.trial_services', True, False, True),
    ('main.live_services', False, False, False)
])
def test_should_order_services_by_usage_with_inactive_last(
    endpoint,
    restricted,
    research_mode,
    trial_mode_services,
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
                                                        'only_active': ANY,
                                                        'trial_mode_services': trial_mode_services})
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
