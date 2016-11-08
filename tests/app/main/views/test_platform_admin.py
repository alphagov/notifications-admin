from datetime import date

from flask import url_for
from freezegun import freeze_time
import pytest
from bs4 import BeautifulSoup

from tests.conftest import mock_get_user
from tests import service_json

from app.main.views.platform_admin import get_statistics, format_stats_by_service, create_global_stats


def test_should_redirect_if_not_logged_in(app_):
    with app_.test_request_context():
        with app_.test_client() as client:
            response = client.get(url_for('main.platform_admin'))
            assert response.status_code == 302
            assert url_for('main.index', _external=True) in response.location


def test_should_403_if_not_platform_admin(app_, active_user_with_permissions, mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
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
    app_,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    fake_uuid
):
    services = [service_json(fake_uuid, 'My Service', [], restricted=restricted, research_mode=research_mode)]
    services[0]['statistics'] = create_stats()

    mock_get_detailed_services.return_value = {'data': services}
    with app_.test_request_context():
        with app_.test_client() as client:
            mock_get_user(mocker, user=platform_admin_user)
            client.login(platform_admin_user)
            response = client.get(url_for('main.platform_admin'))

    assert response.status_code == 200
    mock_get_detailed_services.assert_called_once_with({'detailed': True})
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    # get second column, which contains flags as text.
    assert page.find_all('tbody')[table_index].find_all('td')[1].text.strip() == displayed


def test_should_render_platform_admin_page(
    app_,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
):
    with app_.test_request_context():
        with app_.test_client() as client:
            mock_get_user(mocker, user=platform_admin_user)
            client.login(platform_admin_user)
            response = client.get(url_for('main.platform_admin'))

    assert response.status_code == 200
    resp_data = response.get_data(as_text=True)
    assert 'Platform admin' in resp_data
    assert 'Today' in resp_data
    assert 'Live services' in resp_data
    assert 'Trial mode services' in resp_data
    mock_get_detailed_services.assert_called_once_with({'detailed': True})


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


def test_format_stats_by_service_sums_values_for_sending(fake_uuid):
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
    assert ret[0]['sending'] == 34
    assert ret[0]['delivered'] == 10
    assert ret[0]['failed'] == 16


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
    table_index
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
    mock_get_detailed_services.assert_called_once_with({'detailed': True})
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    rows = page.find_all('tbody')[table_index].find_all('tr')
    assert len(rows)
    assert rows[0]
    assert rows[1]
    assert rows[0].td.text.strip() == 'A'
    assert rows[1].td.text.strip() == 'B'
    assert rows[2].td.text.strip() == 'C'


@pytest.mark.parametrize('research_mode', (True, False))
def test_shows_archived_label_instead_of_live_or_research_mode_label(
    client,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    research_mode
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
    flags = page.find_all('tbody')[0].tr.find_all('td')[1]
    # get second column, which contains flags as text.
    assert flags.text.strip() == 'archived'
