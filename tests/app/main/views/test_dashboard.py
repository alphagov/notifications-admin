from datetime import datetime
import copy
from flask import url_for

import pytest
from bs4 import BeautifulSoup
from freezegun import freeze_time

from app.main.views.dashboard import (
    get_dashboard_totals,
    format_weekly_stats_to_list,
    get_free_paid_breakdown_for_billable_units
)

from tests import validate_route_permission
from tests.conftest import SERVICE_ONE_ID

stub_template_stats = [
    {
        'template_type': 'sms',
        'template_name': 'one',
        'template_id': 'id-1',
        'count': 100
    },
    {
        'template_type': 'email',
        'template_name': 'two',
        'template_id': 'id-2',
        'count': 200
    }
]


def test_get_started(
        app_,
        mocker,
        api_user_active,
        mock_get_service,
        mock_get_service_templates_when_no_templates_exist,
        mock_get_user,
        mock_get_user_by_email,
        mock_login,
        mock_get_jobs,
        mock_has_permissions,
        mock_get_detailed_service,
        mock_get_usage
):
    mock_template_stats = mocker.patch('app.template_statistics_client.get_template_statistics_for_service',
                                       return_value=copy.deepcopy(stub_template_stats))

    with app_.test_request_context(), app_.test_client() as client:
        client.login(api_user_active)
        response = client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    # mock_get_service_templates_when_no_templates_exist.assert_called_once_with(SERVICE_ONE_ID)
    assert response.status_code == 200
    assert 'Get started' in response.get_data(as_text=True)


def test_get_started_is_hidden_once_templates_exist(
        app_,
        mocker,
        api_user_active,
        mock_get_service,
        mock_get_service_templates,
        mock_get_user,
        mock_get_user_by_email,
        mock_login,
        mock_get_jobs,
        mock_has_permissions,
        mock_get_detailed_service,
        mock_get_usage
):
    mock_template_stats = mocker.patch('app.template_statistics_client.get_template_statistics_for_service',
                                       return_value=copy.deepcopy(stub_template_stats))
    with app_.test_request_context(), app_.test_client() as client:
        client.login(api_user_active)
        response = client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    # mock_get_service_templates.assert_called_once_with(SERVICE_ONE_ID)
    assert response.status_code == 200
    assert 'Get started' not in response.get_data(as_text=True)


def test_should_show_recent_templates_on_dashboard(app_,
                                                   mocker,
                                                   api_user_active,
                                                   mock_get_service,
                                                   mock_get_service_templates,
                                                   mock_get_user,
                                                   mock_get_user_by_email,
                                                   mock_login,
                                                   mock_get_jobs,
                                                   mock_has_permissions,
                                                   mock_get_detailed_service,
                                                   mock_get_usage):
    mock_template_stats = mocker.patch('app.template_statistics_client.get_template_statistics_for_service',
                                       return_value=copy.deepcopy(stub_template_stats))

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

        assert response.status_code == 200
        response.get_data(as_text=True)
        mock_template_stats.assert_called_once_with(SERVICE_ONE_ID, limit_days=7)

        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        headers = [header.text.strip() for header in page.find_all('h2') + page.find_all('h1')]
        assert 'Test Service' in headers
        assert 'In the last 7 days' in headers

        table_rows = page.find_all('tbody')[1].find_all('tr')

        assert len(table_rows) == 2

        assert 'two' in table_rows[0].find_all('th')[0].text
        assert 'Email template' in table_rows[0].find_all('th')[0].text
        assert '200' in table_rows[0].find_all('td')[0].text

        assert 'one' in table_rows[1].find_all('th')[0].text
        assert 'Text message template' in table_rows[1].find_all('th')[0].text
        assert '100' in table_rows[1].find_all('td')[0].text


def test_should_show_all_templates_on_template_statistics_page(
        app_,
        mocker,
        api_user_active,
        mock_get_service,
        mock_get_service_templates,
        mock_get_user,
        mock_get_user_by_email,
        mock_login,
        mock_get_jobs,
        mock_has_permissions
):
    mock_template_stats = mocker.patch('app.template_statistics_client.get_template_statistics_for_service',
                                       return_value=copy.deepcopy(stub_template_stats))

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.template_history', service_id=SERVICE_ONE_ID))

        assert response.status_code == 200
        response.get_data(as_text=True)
        mock_template_stats.assert_called_once_with(SERVICE_ONE_ID)

        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        table_rows = page.find_all('tbody')[0].find_all('tr')

        assert len(table_rows) == 2

        assert 'two' in table_rows[0].find_all('th')[0].text
        assert 'Email template' in table_rows[0].find_all('th')[0].text
        assert '200' in table_rows[0].find_all('td')[0].text

        assert 'one' in table_rows[1].find_all('th')[0].text
        assert 'Text message template' in table_rows[1].find_all('th')[0].text
        assert '100' in table_rows[1].find_all('td')[0].text


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_upcoming_jobs_on_dashboard(
    app_,
    mocker,
    api_user_active,
    mock_get_service,
    mock_get_service_templates,
    mock_get_user,
    mock_get_user_by_email,
    mock_login,
    mock_get_template_statistics,
    mock_get_detailed_service,
    mock_get_jobs,
    mock_has_permissions,
    mock_get_usage
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(api_user_active)
        response = client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    mock_get_jobs.assert_called_once_with(SERVICE_ONE_ID, limit_days=7)
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    table_rows = page.find_all('tbody')[0].find_all('tr')
    assert len(table_rows) == 2

    assert 'send_me_later.csv' in table_rows[0].find_all('th')[0].text
    assert 'Sending at 11:09am' in table_rows[0].find_all('th')[0].text
    assert table_rows[0].find_all('td')[0].text.strip() == '1'
    assert 'even_later.csv' in table_rows[1].find_all('th')[0].text
    assert 'Sending at 11:09pm' in table_rows[1].find_all('th')[0].text
    assert table_rows[1].find_all('td')[0].text.strip() == '1'


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_recent_jobs_on_dashboard(
    app_,
    mocker,
    api_user_active,
    mock_get_service,
    mock_get_service_templates,
    mock_get_user,
    mock_get_user_by_email,
    mock_login,
    mock_get_template_statistics,
    mock_get_detailed_service,
    mock_get_jobs,
    mock_has_permissions,
    mock_get_usage
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(api_user_active)
        response = client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    mock_get_jobs.assert_called_once_with(SERVICE_ONE_ID, limit_days=7)
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    table_rows = page.find_all('tbody')[2].find_all('tr')

    assert "Test message" not in page.text
    assert len(table_rows) == 4

    for index, filename in enumerate((
            "export 1/1/2016.xls",
            "all email addresses.xlsx",
            "applicants.ods",
            "thisisatest.csv",
    )):
        assert filename in table_rows[index].find_all('th')[0].text
        assert 'Sent 1 January at 11:09' in table_rows[index].find_all('th')[0].text
        for column_index, count in enumerate((1, 0, 0)):
            assert table_rows[index].find_all('td')[column_index].text.strip() == str(count)


@freeze_time("2016-12-31 11:09:00.061258")
def test_usage_page(
    client,
    api_user_active,
    mock_get_service,
    mock_get_user,
    mock_has_permissions,
    mock_get_usage,
    mock_get_billable_units
):
    client.login(api_user_active)
    response = client.get(url_for('main.usage', service_id=SERVICE_ONE_ID, year=2000))

    assert response.status_code == 200

    mock_get_billable_units.assert_called_once_with(SERVICE_ONE_ID, 2000)

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    cols = page.find_all('div', {'class': 'column-half'})

    assert cols[1].text.strip() == 'Financial year 2000 to 2001'

    assert '123' in cols[2].text
    assert 'Emails' in cols[2].text

    assert '456,123' in cols[3].text
    assert 'Text messages' in cols[3].text

    table = page.find('table').text.strip()

    assert 'April' in table
    assert 'March' in table
    assert '123 free text messages' in table
    assert '£3,403.06' in table
    assert '249,877 free text messages' in table
    assert '206,246 text messages at 1.65p' in table


@freeze_time("2016-12-31 11:09:00.061258")
def test_usage_page_for_invalid_year(
    client,
    api_user_active,
    mock_get_service,
    mock_get_user,
    mock_has_permissions
):
    client.login(api_user_active)
    assert client.get(url_for('main.usage', service_id=SERVICE_ONE_ID, year='abcd')).status_code == 404


def _test_dashboard_menu(mocker, app_, usr, service, permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            usr._permissions[str(service['id'])] = permissions
            mocker.patch('app.user_api_client.check_verify_code', return_value=(True, ''))
            mocker.patch('app.service_api_client.get_services', return_value={'data': [service]})
            mocker.patch('app.user_api_client.get_user', return_value=usr)
            mocker.patch('app.user_api_client.get_user_by_email', return_value=usr)
            mocker.patch('app.service_api_client.get_service', return_value={'data': service})
            client.login(usr)
            return client.get(url_for('main.service_dashboard', service_id=service['id']))


def test_menu_send_messages(mocker,
                            app_,
                            api_user_active,
                            service_one,
                            mock_get_service_templates,
                            mock_get_jobs,
                            mock_get_template_statistics,
                            mock_get_detailed_service,
                            mock_get_usage):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['view_activity', 'send_texts', 'send_emails', 'send_letters'])
        page = resp.get_data(as_text=True)
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='email') in page
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='sms') in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page

        assert url_for('main.service_settings', service_id=service_one['id']) not in page
        assert url_for('main.api_keys', service_id=service_one['id']) not in page
        assert url_for('main.show_all_services') not in page
        assert url_for('main.view_providers') not in page


def test_menu_manage_service(mocker,
                             app_,
                             api_user_active,
                             service_one,
                             mock_get_service_templates,
                             mock_get_jobs,
                             mock_get_template_statistics,
                             mock_get_detailed_service,
                             mock_get_usage):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['view_activity', 'manage_users', 'manage_templates', 'manage_settings'])
        page = resp.get_data(as_text=True)
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='email') in page
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='sms') in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page
        assert url_for('main.service_settings', service_id=service_one['id']) in page

        assert url_for('main.api_keys', service_id=service_one['id']) not in page
        assert url_for('main.show_all_services') not in page


def test_menu_manage_api_keys(mocker,
                              app_,
                              api_user_active,
                              service_one,
                              mock_get_service_templates,
                              mock_get_jobs,
                              mock_get_template_statistics,
                              mock_get_detailed_service,
                              mock_get_usage):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['view_activity', 'manage_api_keys'])
        page = resp.get_data(as_text=True)
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='email') in page
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='sms') in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page
        assert url_for('main.service_settings', service_id=service_one['id']) not in page
        assert url_for('main.show_all_services') not in page

        assert url_for('main.api_integration', service_id=service_one['id']) in page


def test_menu_all_services_for_platform_admin_user(mocker,
                                                   app_,
                                                   platform_admin_user,
                                                   service_one,
                                                   mock_get_service_templates,
                                                   mock_get_jobs,
                                                   mock_get_template_statistics,
                                                   mock_get_detailed_service,
                                                   mock_get_usage):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            platform_admin_user,
            service_one,
            [])
        page = resp.get_data(as_text=True)
        assert url_for('main.choose_template', service_id=service_one['id'], template_type='sms') in page
        assert url_for('main.choose_template', service_id=service_one['id'], template_type='email') in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page
        assert url_for('main.service_settings', service_id=service_one['id']) in page
        assert url_for('main.view_notifications', service_id=service_one['id'], message_type='email') in page
        assert url_for('main.view_notifications', service_id=service_one['id'], message_type='sms') in page
        assert url_for('main.api_keys', service_id=service_one['id']) not in page


def test_route_for_service_permissions(mocker,
                                       app_,
                                       api_user_active,
                                       service_one,
                                       mock_get_service,
                                       mock_get_user,
                                       mock_get_service_templates,
                                       mock_get_jobs,
                                       mock_get_template_statistics,
                                       mock_get_detailed_service,
                                       mock_get_usage):
    routes = [
        'main.service_dashboard']
    with app_.test_request_context():
        # Just test that the user is part of the service
        for route in routes:
            validate_route_permission(
                mocker,
                app_,
                "GET",
                200,
                url_for(
                    route,
                    service_id=service_one['id']),
                ['view_activity'],
                api_user_active,
                service_one)


def test_aggregate_template_stats():
    from app.main.views.dashboard import aggregate_usage
    expected = aggregate_usage(copy.deepcopy(stub_template_stats))

    assert len(expected) == 2
    assert expected[0]['template_name'] == 'two'
    assert expected[0]['count'] == 200
    assert expected[0]['template_id'] == 'id-2'
    assert expected[0]['template_type'] == 'email'
    assert expected[1]['template_name'] == 'one'
    assert expected[1]['count'] == 100
    assert expected[1]['template_id'] == 'id-1'
    assert expected[1]['template_type'] == 'sms'


def test_service_dashboard_updates_gets_dashboard_totals(mocker,
                                                         app_,
                                                         active_user_with_permissions,
                                                         service_one,
                                                         mock_get_user,
                                                         mock_get_service_templates,
                                                         mock_get_template_statistics,
                                                         mock_get_detailed_service,
                                                         mock_get_jobs,
                                                         mock_get_usage):
    dashboard_totals = mocker.patch('app.main.views.dashboard.get_dashboard_totals', return_value={
        'email': {'requested': 123, 'delivered': 0, 'failed': 0},
        'sms': {'requested': 456, 'delivered': 0, 'failed': 0}
    })

    with app_.test_request_context(), app_.test_client() as client:
        client.login(active_user_with_permissions, mocker, service_one)
        response = client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    numbers = [number.text.strip() for number in page.find_all('div', class_='big-number-number')]
    assert '123' in numbers
    assert '456' in numbers

    table_rows = page.find_all('tbody')[0].find_all('tr')


def test_get_dashboard_totals_adds_percentages():
    stats = {
        'sms': {
            'requested': 3,
            'delivered': 0,
            'failed': 2
        },
        'email': {
            'requested': 0,
            'delivered': 0,
            'failed': 0
        }
    }
    assert get_dashboard_totals(stats)['sms']['failed_percentage'] == '66.7'
    assert get_dashboard_totals(stats)['email']['failed_percentage'] == '0'


@pytest.mark.parametrize(
    'failures,expected', [
        (2, False),
        (3, False),
        (4, True)
    ]
)
def test_get_dashboard_totals_adds_warning(failures, expected):
    stats = {
        'sms': {
            'requested': 100,
            'delivered': 0,
            'failed': failures
        }
    }
    assert get_dashboard_totals(stats)['sms']['show_warning'] == expected


def test_format_weekly_stats_to_list_empty_case():
    assert format_weekly_stats_to_list({}) == []


def test_format_weekly_stats_to_list_sorts_by_week():
    stats = {
        '2016-07-04': {},
        '2016-07-11': {},
        '2016-07-18': {},
        '2016-07-25': {}
    }
    resp = format_weekly_stats_to_list(stats)
    assert resp[0]['week_start'] == '2016-07-25'
    assert resp[1]['week_start'] == '2016-07-18'
    assert resp[2]['week_start'] == '2016-07-11'
    assert resp[3]['week_start'] == '2016-07-04'


def test_format_weekly_stats_to_list_includes_datetime_for_comparison():
    stats = {
        '2016-07-25': {}
    }
    resp = format_weekly_stats_to_list(stats)
    assert resp == [{
        'week_start': '2016-07-25',
        'week_end': '2016-07-31',
        'week_end_datetime': datetime(2016, 7, 31, 0, 0, 0)
    }]


def test_format_weekly_stats_to_list_has_stats_with_failure_rate():
    stats = {
        '2016-07-25': {'sms': _stats(3, 1, 2)}
    }
    resp = format_weekly_stats_to_list(stats)
    assert resp[0]['sms']['failure_rate'] == '66.7'
    assert resp[0]['sms']['requested'] == 3


def _stats(requested, delivered, failed):
    return {'requested': requested, 'delivered': delivered, 'failed': failed}


@pytest.mark.parametrize(
    'now, expected_number_of_months', [
        (freeze_time("2017-12-31 11:09:00.061258"), 12),
        (freeze_time("2017-01-01 11:09:00.061258"), 10)
    ]
)
def test_get_free_paid_breakdown_for_billable_units(now, expected_number_of_months):
    with now:
        assert list(get_free_paid_breakdown_for_billable_units(
            2016, {
                'April': 100000,
                'May': 100000,
                'June': 100000,
                'February': 1234
            }
        )) == [
            {'name': 'April', 'free': 100000, 'paid': 0},
            {'name': 'May', 'free': 100000, 'paid': 0},
            {'name': 'June', 'free': 50000, 'paid': 50000},
            {'name': 'July', 'free': 0, 'paid': 0},
            {'name': 'August', 'free': 0, 'paid': 0},
            {'name': 'September', 'free': 0, 'paid': 0},
            {'name': 'October', 'free': 0, 'paid': 0},
            {'name': 'November', 'free': 0, 'paid': 0},
            {'name': 'December', 'free': 0, 'paid': 0},
            {'name': 'January', 'free': 0, 'paid': 0},
            {'name': 'February', 'free': 0, 'paid': 1234},
            {'name': 'March', 'free': 0, 'paid': 0}
        ][:expected_number_of_months]
