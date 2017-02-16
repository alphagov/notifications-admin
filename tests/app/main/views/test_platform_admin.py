import datetime

from flask import url_for
import pytest
from bs4 import BeautifulSoup

from tests.conftest import mock_get_user
from tests import service_json

from app.main.views.platform_admin import format_stats_by_service, create_global_stats


def test_should_redirect_if_not_logged_in(
    client
):
    response = client.get(url_for('main.platform_admin'))
    assert response.status_code == 302
    assert response.location == url_for('main.sign_in', next=url_for('main.platform_admin'), _external=True)


def test_should_403_if_not_platform_admin(
    client,
    active_user_with_permissions,
    mocker,
):
    mock_get_user(mocker, user=active_user_with_permissions)
    client.login(active_user_with_permissions)
    response = client.get(url_for('main.platform_admin'))

    assert response.status_code == 403


@pytest.mark.parametrize('restricted, table_index, research_mode, displayed', [
    (True, 1, False, ''),
    (False, 0, False, 'Live'),
    (False, 0, True, 'research mode'),
    (True, 1, True, 'research mode')
])
def test_should_show_research_and_restricted_mode(
    restricted,
    table_index,
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
    response = client.get(url_for('main.platform_admin'))

    assert response.status_code == 200
    mock_get_detailed_services.assert_called_once_with({'detailed': True, 'include_from_test_key': True})
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    # get first column in second row, which contains flags as text.
    table_body = page.find_all('table')[table_index].find_all('tbody')[0]
    service_mode = table_body.find_all('tbody')[0].find_all('tr')[1].find_all('td')[0].text.strip()
    assert service_mode == displayed


def test_should_render_platform_admin_page(
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for('main.platform_admin'))

    assert response.status_code == 200
    resp_data = response.get_data(as_text=True)
    assert 'Platform admin' in resp_data
    assert 'Live services' in resp_data
    assert 'Trial mode services' in resp_data
    mock_get_detailed_services.assert_called_once_with({'detailed': True, 'include_from_test_key': True})


@pytest.mark.parametrize('include_from_test_key, api_args', [
    ("Y", {'detailed': True, 'include_from_test_key': True}),
    ("N", {'detailed': True, 'include_from_test_key': False})
])
def test_platform_admin_toggle_including_from_test_key(
    include_from_test_key,
    api_args,
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for('main.platform_admin', include_from_test_key=include_from_test_key))

    assert response.status_code == 200
    mock_get_detailed_services.assert_called_once_with(api_args)


def test_platform_admin_with_date_filter(
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user)
    response = client.get(url_for('main.platform_admin', start_date='2016-12-20', end_date='2016-12-28'))

    assert response.status_code == 200
    resp_data = response.get_data(as_text=True)
    assert 'Platform admin' in resp_data
    assert 'Live services' in resp_data
    assert 'Trial mode services' in resp_data
    mock_get_detailed_services.assert_called_once_with({
        'include_from_test_key': False,
        'start_date': datetime.date(2016, 12, 20),
        'end_date': datetime.date(2016, 12, 28),
        'detailed': True,
    })


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
        }
    }


def create_stats(
    emails_requested=0,
    emails_delivered=0,
    emails_failed=0,
    sms_requested=0,
    sms_delivered=0,
    sms_failed=0
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
        }
    }


def test_format_stats_by_service_returns_correct_values(fake_uuid):
    services = [service_json(fake_uuid, 'a', [])]
    services[0]['statistics'] = create_stats(
        emails_requested=10,
        emails_delivered=3,
        emails_failed=5,
        sms_requested=50,
        sms_delivered=7,
        sms_failed=11
    )

    ret = list(format_stats_by_service(services))
    assert len(ret) == 1

    assert ret[0]['stats']['email']['sending'] == 2
    assert ret[0]['stats']['email']['delivered'] == 3
    assert ret[0]['stats']['email']['failed'] == 5

    assert ret[0]['stats']['sms']['sending'] == 32
    assert ret[0]['stats']['sms']['delivered'] == 7
    assert ret[0]['stats']['sms']['failed'] == 11


@pytest.mark.parametrize('restricted, table_index, research_mode', [
    (True, 1, False),
    (False, 0, False)
])
def test_should_show_email_and_sms_stats_for_all_service_types(
    restricted,
    table_index,
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
    response = client.get(url_for('main.platform_admin'))

    assert response.status_code == 200
    mock_get_detailed_services.assert_called_once_with({'detailed': True, 'include_from_test_key': True})
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    table_body = page.find_all('table')[table_index].find_all('tbody')[0]
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


@pytest.mark.parametrize('restricted, table_index', [
    (False, 0),
    (True, 1)
], ids=['live', 'trial'])
def test_should_show_archived_services_last(
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    restricted,
    table_index,
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
    response = client.get(url_for('main.platform_admin'))

    assert response.status_code == 200
    mock_get_detailed_services.assert_called_once_with({'detailed': True, 'include_from_test_key': True})
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    table_body = page.find_all('table')[table_index].find_all('tbody')[0]
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
    response = client.get(url_for('main.platform_admin'))

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
        sms_failed=30
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

    assert email_total == 60
    assert sms_total == 40
