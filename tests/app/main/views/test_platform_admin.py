from datetime import date

from flask import url_for
from freezegun import freeze_time

from tests.conftest import mock_get_user

from app.main.views.platform_admin import get_global_stats


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


def test_should_render_platform_admin_page(app_, platform_admin_user, mocker, mock_get_all_service_statistics):
    with app_.test_request_context():
        with app_.test_client() as client:
            mock_get_user(mocker, user=platform_admin_user)
            client.login(platform_admin_user)
            response = client.get(url_for('main.platform_admin'))

            assert response.status_code == 200
            resp_data = response.get_data(as_text=True)
            assert 'Platform admin' in resp_data
            assert 'List all services' in resp_data
            assert 'View providers' in resp_data


def test_get_global_stats_should_summarise_all_stats(mock_get_all_service_statistics):
    resp = get_global_stats()

    assert 'emails_delivered' in resp
    assert 'emails_failed' in resp
    assert 'emails_failure_rate' in resp
    assert 'sms_delivered' in resp
    assert 'sms_failed' in resp
    assert 'sms_failure_rate' in resp


@freeze_time('2000-06-30T23:30:00', tz_offset=0)
def test_get_global_stats_should_query_for_today_forced_to_GMT(mock_get_all_service_statistics):
    get_global_stats()

    mock_get_all_service_statistics.assert_called_once_with(date(2000, 7, 1))
