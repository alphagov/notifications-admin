from datetime import date

from flask import url_for
from freezegun import freeze_time

from tests.conftest import mock_get_user

from app.main.views.platform_admin import get_statistics, format_stats_by_service


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


def test_should_render_platform_admin_page(
    app_,
    platform_admin_user,
    mocker,
    mock_get_services,
    mock_get_all_service_statistics
):
    with app_.test_request_context():
        with app_.test_client() as client:
            mock_get_user(mocker, user=platform_admin_user)
            client.login(platform_admin_user)
            response = client.get(url_for('main.platform_admin'))

            assert response.status_code == 200
            resp_data = response.get_data(as_text=True)
            assert 'Platform admin' in resp_data
            assert 'Today\'s statistics' in resp_data
            assert 'Services' in resp_data


def test_get_statistics_should_summarise_all_stats(mock_get_all_service_statistics, mock_get_services):
    resp = get_statistics()['global_stats']

    assert 'emails_delivered' in resp
    assert 'emails_failed' in resp
    assert 'emails_failure_rate' in resp
    assert 'sms_delivered' in resp
    assert 'sms_failed' in resp
    assert 'sms_failure_rate' in resp


@freeze_time('2000-06-30T23:30:00', tz_offset=0)
def test_get_statistics_should_query_for_today_forced_to_GMT(mock_get_all_service_statistics, mock_get_services):
    get_statistics()

    mock_get_all_service_statistics.assert_called_once_with(date(2000, 7, 1))


def create_stats(
    service,
    emails_requested=0,
    emails_delivered=0,
    emails_failed=0,
    sms_requested=0,
    sms_delivered=0,
    sms_failed=0
):
    return {
        'service': service,
        'emails_requested': emails_requested,
        'emails_delivered': emails_delivered,
        'emails_failed': emails_failed,
        'sms_requested': sms_requested,
        'sms_delivered': sms_delivered,
        'sms_failed': sms_failed,
    }


def test_format_stats_by_service_gets_correct_stats_for_each_service():
    services = [
        {'name': 'a', 'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'},
        {'name': 'b', 'id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'}
    ]
    all_stats = [
        create_stats('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', emails_requested=1),
        create_stats('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', emails_requested=2)
    ]

    ret = format_stats_by_service(all_stats, services)

    assert len(ret) == 2
    assert ret[0]['name'] == 'a'
    assert ret[0]['sending'] == 1
    assert ret[0]['delivered'] == 0
    assert ret[0]['failed'] == 0

    assert ret[1]['name'] == 'b'
    assert ret[1]['sending'] == 2
    assert ret[1]['delivered'] == 0
    assert ret[1]['failed'] == 0


def test_format_stats_by_service_sums_values_for_sending():
    services = [
        {'name': 'a', 'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'},
    ]
    all_stats = [
        create_stats(
            'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            emails_requested=10,
            emails_delivered=3,
            emails_failed=5,
            sms_requested=50,
            sms_delivered=7,
            sms_failed=11
        )
    ]

    ret = format_stats_by_service(all_stats, services)

    assert len(ret) == 1
    assert ret[0]['sending'] == 34
    assert ret[0]['delivered'] == 10
    assert ret[0]['failed'] == 16
