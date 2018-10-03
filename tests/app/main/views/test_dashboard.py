import copy
import json
from datetime import datetime
from functools import partial
from unittest.mock import call

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from freezegun import freeze_time

from app.main.views.dashboard import (
    aggregate_status_types,
    format_monthly_stats_to_list,
    format_template_stats_to_list,
    get_dashboard_totals,
    get_free_paid_breakdown_for_billable_units,
    get_tuples_of_financial_years,
)
from tests import (
    validate_route_permission,
    validate_route_permission_with_client,
)
from tests.conftest import (
    SERVICE_ONE_ID,
    active_caseworking_user,
    active_user_view_permissions,
    mock_get_inbound_sms_summary,
    mock_get_inbound_sms_summary_with_no_messages,
    normalize_spaces,
)

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
    },
    {
        'template_type': 'letter',
        'template_name': 'three',
        'template_id': 'id-3',
        'count': 300
    },
    {
        'template_type': 'letter',
        'template_name': 'four',
        'template_id': 'id-4',
        'count': 400,
        'is_precompiled_letter': True
    }
]


@pytest.mark.parametrize('user', (
    active_user_view_permissions,
    active_caseworking_user,
))
def test_redirect_from_old_dashboard(
    logged_in_client,
    user,
    mocker,
    fake_uuid,
):
    mocker.patch('app.user_api_client.get_user', return_value=user(fake_uuid))
    expected_location = 'http://localhost/services/{}'.format(SERVICE_ONE_ID)

    response = logged_in_client.get('/services/{}/dashboard'.format(SERVICE_ONE_ID))

    assert response.status_code == 302
    assert response.location == expected_location
    assert expected_location == url_for('main.service_dashboard', service_id=SERVICE_ONE_ID, _external=True)


def test_redirect_caseworkers_to_templates(
    client_request,
    mocker,
    active_caseworking_user,
):
    mocker.patch('app.user_api_client.get_user', return_value=active_caseworking_user)
    client_request.get(
        'main.service_dashboard',
        service_id=SERVICE_ONE_ID,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.choose_template',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )


def test_get_started(
    logged_in_client,
    mocker,
    mock_get_service_templates_when_no_templates_exist,
    mock_get_jobs,
    mock_get_service_statistics,
    mock_get_usage,
    mock_get_inbound_sms_summary
):
    mocker.patch(
        'app.template_statistics_client.get_template_statistics_for_service',
        return_value=copy.deepcopy(stub_template_stats)
    )

    response = logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    # mock_get_service_templates_when_no_templates_exist.assert_called_once_with(SERVICE_ONE_ID)
    assert response.status_code == 200
    assert 'Get started' in response.get_data(as_text=True)


def test_get_started_is_hidden_once_templates_exist(
    logged_in_client,
    mocker,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_service_statistics,
    mock_get_usage,
    mock_get_inbound_sms_summary
):
    mocker.patch(
        'app.template_statistics_client.get_template_statistics_for_service',
        return_value=copy.deepcopy(stub_template_stats)
    )
    response = logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    # mock_get_service_templates.assert_called_once_with(SERVICE_ONE_ID)
    assert response.status_code == 200
    assert 'Get started' not in response.get_data(as_text=True)


def test_inbound_messages_not_visible_to_service_without_permissions(
    logged_in_client,
    service_one,
    mock_get_service_templates_when_no_templates_exist,
    mock_get_jobs,
    mock_get_service_statistics,
    mock_get_template_statistics,
    mock_get_usage,
    mock_get_inbound_sms_summary
):

    service_one['permissions'] = []

    response = logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert response.status_code == 200
    assert not page.select('.big-number-meta-wrapper')
    assert mock_get_inbound_sms_summary.called is False


@pytest.mark.parametrize('inbound_summary_mock, expected_text', [
    (mock_get_inbound_sms_summary_with_no_messages, '0 text messages received'),
    (mock_get_inbound_sms_summary, '99 text messages received latest message just now'),
])
def test_inbound_messages_shows_count_of_messages(
    logged_in_client,
    mocker,
    service_one,
    mock_get_service_templates_when_no_templates_exist,
    mock_get_jobs,
    mock_get_service_statistics,
    mock_get_template_statistics,
    mock_get_usage,
    inbound_summary_mock,
    expected_text
):

    service_one['permissions'] = ['inbound_sms']
    inbound_summary_mock(mocker)

    response = logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert response.status_code == 200
    assert normalize_spaces(page.select('.big-number-meta-wrapper')[0].text) == expected_text
    assert page.select('.big-number-meta-wrapper a')[0]['href'] == url_for(
        'main.inbox', service_id=SERVICE_ONE_ID
    )


@pytest.mark.parametrize('index, expected_row', enumerate([
    '07900 900000 message-1 1 hour ago',
    '07900 900000 message-2 1 hour ago',
    '07900 900000 message-3 1 hour ago',
    '07900 900002 message-4 3 hours ago',
    '07900 900004 message-5 5 hours ago',
    '07900 900006 message-6 7 hours ago',
    '07900 900008 message-7 9 hours ago',
    '07900 900008 message-8 9 hours ago',
]))
def test_inbox_showing_inbound_messages(
    logged_in_client,
    service_one,
    mock_get_service_templates_when_no_templates_exist,
    mock_get_jobs,
    mock_get_service_statistics,
    mock_get_template_statistics,
    mock_get_usage,
    mock_get_most_recent_inbound_sms,
    index,
    expected_row,
):

    service_one['permissions'] = ['inbound_sms']

    response = logged_in_client.get(url_for('main.inbox', service_id=SERVICE_ONE_ID))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert response.status_code == 200
    rows = page.select('tbody tr')
    assert len(rows) == 8
    assert normalize_spaces(rows[index].text) == expected_row
    assert page.select_one('a[download]')['href'] == url_for(
        'main.inbox_download',
        service_id=SERVICE_ONE_ID,
    )


def test_get_inbound_sms_shows_page_links(
    logged_in_client,
    service_one,
    mock_get_service_templates_when_no_templates_exist,
    mock_get_jobs,
    mock_get_service_statistics,
    mock_get_template_statistics,
    mock_get_usage,
    mock_get_most_recent_inbound_sms,
    mock_get_inbound_number_for_service,
):
    service_one['permissions'] = ['inbound_sms']

    response = logged_in_client.get(url_for('main.inbox', service_id=SERVICE_ONE_ID, page=2))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Next page' in page.find('li', {'class': 'next-page'}).text
    assert 'Previous page' in page.find('li', {'class': 'previous-page'}).text


def test_empty_inbox(
    logged_in_client,
    service_one,
    mock_get_service_templates_when_no_templates_exist,
    mock_get_jobs,
    mock_get_service_statistics,
    mock_get_template_statistics,
    mock_get_usage,
    mock_get_most_recent_inbound_sms_with_no_messages,
    mock_get_inbound_number_for_service,
):

    service_one['permissions'] = ['inbound_sms']

    response = logged_in_client.get(url_for('main.inbox', service_id=SERVICE_ONE_ID))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert response.status_code == 200
    assert normalize_spaces(page.select('tbody tr')) == (
        'When users text your service’s phone number (0781239871) you’ll see the messages here'
    )
    assert not page.select('a[download]')
    assert not page.select('li.next-page')
    assert not page.select('li.previous-page')


@pytest.mark.parametrize('endpoint', [
    'main.inbox',
    'main.inbox_updates',
])
def test_inbox_not_accessible_to_service_without_permissions(
    logged_in_client,
    service_one,
    endpoint,
):
    service_one['permissions'] = []
    response = logged_in_client.get(url_for(endpoint, service_id=SERVICE_ONE_ID))

    assert response.status_code == 403


def test_anyone_can_see_inbox(
    client,
    api_user_active,
    service_one,
    mocker,
    mock_get_most_recent_inbound_sms_with_no_messages,
    mock_get_inbound_number_for_service,
):

    service_one['permissions'] = ['inbound_sms']

    validate_route_permission_with_client(
        mocker,
        client,
        'GET',
        200,
        url_for('main.inbox', service_id=service_one['id']),
        ['view_activity'],
        api_user_active,
        service_one,
    )


def test_view_inbox_updates(
    logged_in_client,
    service_one,
    mocker,
    mock_get_most_recent_inbound_sms_with_no_messages,
):

    mock_get_partials = mocker.patch(
        'app.main.views.dashboard.get_inbox_partials',
        return_value={'messages': 'foo'},
    )

    response = logged_in_client.get(url_for(
        'main.inbox_updates', service_id=SERVICE_ONE_ID,
    ))

    assert response.status_code == 200
    assert json.loads(response.get_data(as_text=True)) == {'messages': 'foo'}

    mock_get_partials.assert_called_once_with(SERVICE_ONE_ID)


@freeze_time("2016-07-01 13:00")
def test_download_inbox(
    logged_in_client,
    mock_get_inbound_sms,
):
    response = logged_in_client.get(
        url_for('main.inbox_download', service_id=SERVICE_ONE_ID)
    )
    assert response.status_code == 200
    assert response.headers['Content-Type'] == (
        'text/csv; '
        'charset=utf-8'
    )
    assert response.headers['Content-Disposition'] == (
        'inline; '
        'filename="Received text messages 2016-07-01.csv"'
    )
    assert response.get_data(as_text=True) == (
        'Phone number,Message,Received\r\n'
        '07900900000,message-1,2016-07-01 13:00\r\n'
        '07900900000,message-2,2016-07-01 12:59\r\n'
        '07900900000,message-3,2016-07-01 12:59\r\n'
        '07900900002,message-4,2016-07-01 10:59\r\n'
        '07900900004,message-5,2016-07-01 08:59\r\n'
        '07900900006,message-6,2016-07-01 06:59\r\n'
        '07900900008,message-7,2016-07-01 04:59\r\n'
        '07900900008,message-8,2016-07-01 04:59\r\n'
    )


@freeze_time("2016-07-01 13:00")
@pytest.mark.parametrize('message_content, expected_cell', [
    ('=2+5', '2+5'),
    ('==2+5', '2+5'),
    ('-2+5', '2+5'),
    ('+2+5', '2+5'),
    ('@2+5', '2+5'),
    ('looks safe,=2+5', '"looks safe,=2+5"'),
])
def test_download_inbox_strips_formulae(
    mocker,
    logged_in_client,
    fake_uuid,
    message_content,
    expected_cell,
):

    mocker.patch(
        'app.service_api_client.get_inbound_sms',
        return_value={
            'has_next': False,
            'data': [{
                'user_number': 'elevenchars',
                'notify_number': 'foo',
                'content': message_content,
                'created_at': datetime.utcnow().isoformat(),
                'id': fake_uuid,
            }]
        },
    )
    response = logged_in_client.get(
        url_for('main.inbox_download', service_id=SERVICE_ONE_ID)
    )
    assert expected_cell in response.get_data(as_text=True).split('\r\n')[1]


def test_should_show_recent_templates_on_dashboard(
    logged_in_client,
    mocker,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_service_statistics,
    mock_get_usage,
    mock_get_inbound_sms_summary
):
    mock_template_stats = mocker.patch('app.template_statistics_client.get_template_statistics_for_service',
                                       return_value=copy.deepcopy(stub_template_stats))

    response = logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    assert response.status_code == 200
    response.get_data(as_text=True)
    mock_template_stats.assert_called_once_with(SERVICE_ONE_ID, limit_days=7)

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    headers = [header.text.strip() for header in page.find_all('h2') + page.find_all('h1')]
    assert 'In the last 7 days' in headers

    table_rows = page.find_all('tbody')[1].find_all('tr')

    assert len(table_rows) == 4

    assert 'Provided as PDF' in table_rows[0].find_all('th')[0].text
    assert 'Letter' in table_rows[0].find_all('th')[0].text
    assert '400' in table_rows[0].find_all('td')[0].text

    assert 'three' in table_rows[1].find_all('th')[0].text
    assert 'Letter template' in table_rows[1].find_all('th')[0].text
    assert '300' in table_rows[1].find_all('td')[0].text

    assert 'two' in table_rows[2].find_all('th')[0].text
    assert 'Email template' in table_rows[2].find_all('th')[0].text
    assert '200' in table_rows[2].find_all('td')[0].text

    assert 'one' in table_rows[3].find_all('th')[0].text
    assert 'Text message template' in table_rows[3].find_all('th')[0].text
    assert '100' in table_rows[3].find_all('td')[0].text


@freeze_time("2016-07-01 12:00")  # 4 months into 2016 financial year
@pytest.mark.parametrize('partial_url', [
    partial(url_for),
    partial(url_for, year='2016'),
])
def test_should_show_redirect_from_template_history(
        logged_in_client,
        partial_url,
):
    response = logged_in_client.get(
        partial_url('main.template_history', service_id=SERVICE_ONE_ID, _external=True)
    )

    assert response.status_code == 301


@freeze_time("2016-07-01 12:00")  # 4 months into 2016 financial year
@pytest.mark.parametrize('partial_url', [
    partial(url_for),
    partial(url_for, year='2016'),
])
def test_should_show_monthly_breakdown_of_template_usage(
    logged_in_client,
    mock_get_monthly_template_usage,
    partial_url,
):
    response = logged_in_client.get(
        partial_url('main.template_usage', service_id=SERVICE_ONE_ID, _external=True)
    )

    assert response.status_code == 200
    mock_get_monthly_template_usage.assert_called_once_with(SERVICE_ONE_ID, 2016)

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    table_rows = page.select('tbody tr')

    assert ' '.join(table_rows[0].text.split()) == (
        'My first template '
        'Text message template '
        '2'
    )

    assert len(table_rows) == len(['April'])
    assert len(page.select('.table-no-data')) == len(['May', 'June', 'July'])


def test_anyone_can_see_monthly_breakdown(
    client,
    api_user_active,
    service_one,
    mocker,
    mock_get_monthly_notification_stats,
):
    validate_route_permission_with_client(
        mocker,
        client,
        'GET',
        200,
        url_for('main.monthly', service_id=service_one['id']),
        ['view_activity'],
        api_user_active,
        service_one,
    )


def test_monthly_shows_letters_in_breakdown(
    client_request,
    service_one,
    mock_get_monthly_notification_stats,
):
    page = client_request.get(
        'main.monthly',
        service_id=service_one['id']
    )

    columns = page.select('.table-field-center-aligned .big-number-label')

    assert normalize_spaces(columns[0].text) == 'emails'
    assert normalize_spaces(columns[1].text) == 'text messages'
    assert normalize_spaces(columns[2].text) == 'letters'


@pytest.mark.parametrize('endpoint', [
    'main.monthly',
    'main.template_usage',
])
@freeze_time("2015-01-01 15:15:15.000000")
def test_stats_pages_show_last_3_years(
    client_request,
    endpoint,
    mock_get_monthly_notification_stats,
    mock_get_monthly_template_usage,
):
    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
    )

    assert normalize_spaces(page.select_one('.pill').text) == (
        '2012 to 2013 financial year '
        '2013 to 2014 financial year '
        '2014 to 2015 financial year'
    )


def test_monthly_has_equal_length_tables(
    client_request,
    service_one,
    mock_get_monthly_notification_stats,
):
    page = client_request.get(
        'main.monthly',
        service_id=service_one['id']
    )

    assert page.select_one('.table-field-headings th').get('width') == "25%"


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_upcoming_jobs_on_dashboard(
    logged_in_client,
    mock_get_service_templates,
    mock_get_template_statistics,
    mock_get_service_statistics,
    mock_get_jobs,
    mock_get_usage,
    mock_get_inbound_sms_summary
):
    response = logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    second_call = mock_get_jobs.call_args_list[1]
    assert second_call[0] == (SERVICE_ONE_ID,)
    assert second_call[1]['statuses'] == ['scheduled']

    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    table_rows = page.find_all('tbody')[0].find_all('tr')
    assert len(table_rows) == 2

    assert 'send_me_later.csv' in table_rows[0].find_all('th')[0].text
    assert 'Sending today at 11:09am' in table_rows[0].find_all('th')[0].text
    assert table_rows[0].find_all('td')[0].text.strip() == '1'
    assert 'even_later.csv' in table_rows[1].find_all('th')[0].text
    assert 'Sending today at 11:09pm' in table_rows[1].find_all('th')[0].text
    assert table_rows[1].find_all('td')[0].text.strip() == '1'


@pytest.mark.parametrize('permissions, column_name, expected_column_count', [
    (['email', 'sms'], '.column-half', 2),
    (['email', 'letter'], '.column-third', 3),
    (['email', 'sms', 'letter'], '.column-third', 3)
])
def test_correct_columns_display_on_dashboard(
    client_request,
    mock_get_service_templates,
    mock_get_template_statistics,
    mock_get_service_statistics,
    mock_get_jobs,
    service_one,
    permissions,
    expected_column_count,
    column_name
):

    service_one['permissions'] = permissions

    page = client_request.get(
        'main.service_dashboard',
        service_id=service_one['id']
    )

    assert len(page.select(column_name)) == expected_column_count


@pytest.mark.parametrize('permissions, totals, big_number_class, expected_column_count', [
    (
        ['email', 'sms'],
        {
            'email': {'requested': 0, 'delivered': 0, 'failed': 0},
            'sms': {'requested': 999999999, 'delivered': 0, 'failed': 0}
        },
        '.big-number',
        2,
    ),
    (
        ['email', 'sms'],
        {
            'email': {'requested': 1000000000, 'delivered': 0, 'failed': 0},
            'sms': {'requested': 1000000, 'delivered': 0, 'failed': 0}
        },
        '.big-number-smaller',
        2,
    ),
    (
        ['email', 'sms', 'letter'],
        {
            'email': {'requested': 0, 'delivered': 0, 'failed': 0},
            'sms': {'requested': 99999, 'delivered': 0, 'failed': 0},
            'letter': {'requested': 99999, 'delivered': 0, 'failed': 0}
        },
        '.big-number',
        3,
    ),
    (
        ['email', 'sms', 'letter'],
        {
            'email': {'requested': 0, 'delivered': 0, 'failed': 0},
            'sms': {'requested': 0, 'delivered': 0, 'failed': 0},
            'letter': {'requested': 100000, 'delivered': 0, 'failed': 0},
        },
        '.big-number-smaller',
        3,
    ),
])
def test_correct_font_size_for_big_numbers(
    client_request,
    mocker,
    mock_get_service_templates,
    mock_get_template_statistics,
    mock_get_service_statistics,
    mock_get_jobs,
    service_one,
    permissions,
    totals,
    big_number_class,
    expected_column_count,
):

    service_one['permissions'] = permissions

    mocker.patch(
        'app.main.views.dashboard.get_dashboard_totals',
        return_value=totals
    )

    page = client_request.get(
        'main.service_dashboard',
        service_id=service_one['id'],
    )

    assert expected_column_count == len(
        page.select('.big-number-with-status {}'.format(big_number_class))
    )


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_recent_jobs_on_dashboard(
    logged_in_client,
    mock_get_service_templates,
    mock_get_template_statistics,
    mock_get_service_statistics,
    mock_get_jobs,
    mock_get_usage,
    mock_get_inbound_sms_summary
):
    response = logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    third_call = mock_get_jobs.call_args_list[2]
    assert third_call[0] == (SERVICE_ONE_ID,)
    assert third_call[1]['limit_days'] == 7
    assert 'scheduled' not in third_call[1]['statuses']

    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    table_rows = page.find_all('tbody')[2].find_all('tr')

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


@freeze_time("2012-03-31 12:12:12")
def test_usage_page(
    logged_in_client,
    mock_get_usage,
    mock_get_billable_units,
    mock_get_free_sms_fragment_limit
):
    response = logged_in_client.get(url_for('main.usage', service_id=SERVICE_ONE_ID))

    assert response.status_code == 200

    mock_get_billable_units.assert_called_once_with(SERVICE_ONE_ID, 2011)
    mock_get_usage.assert_called_once_with(SERVICE_ONE_ID, 2011)
    mock_get_free_sms_fragment_limit.assert_called_with(SERVICE_ONE_ID, 2011)

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    cols = page.find_all('div', {'class': 'column-half'})
    nav = page.find('ul', {'class': 'pill', 'role': 'tablist'})
    nav_links = nav.find_all('a')

    assert normalize_spaces(nav_links[0].text) == '2010 to 2011 financial year'
    assert normalize_spaces(nav.find('li', {'aria-selected': 'true'}).text) == '2011 to 2012 financial year'
    assert normalize_spaces(nav_links[1].text) == '2012 to 2013 financial year'
    assert '252,190' in cols[1].text
    assert 'Text messages' in cols[1].text

    table = page.find('table').text.strip()

    assert '249,860 free text messages' in table
    assert '40 free text messages' in table
    assert '960 text messages at 1.65p' in table
    assert 'April' in table
    assert 'February' in table
    assert 'March' in table
    assert '£15.84' in table
    assert '140 free text messages' in table
    assert '£20.30' in table
    assert '1,230 text messages at 1.65p' in table


@freeze_time("2012-03-31 12:12:12")
def test_usage_page_with_letters(
    logged_in_client,
    service_one,
    mock_get_usage,
    mock_get_billable_units,
    mock_get_free_sms_fragment_limit
):
    service_one['permissions'].append('letter')
    response = logged_in_client.get(url_for('main.usage', service_id=SERVICE_ONE_ID))

    assert response.status_code == 200

    mock_get_billable_units.assert_called_once_with(SERVICE_ONE_ID, 2011)
    mock_get_usage.assert_called_once_with(SERVICE_ONE_ID, 2011)
    mock_get_free_sms_fragment_limit.assert_called_with(SERVICE_ONE_ID, 2011)

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    cols = page.find_all('div', {'class': 'column-one-third'})
    nav = page.find('ul', {'class': 'pill', 'role': 'tablist'})
    nav_links = nav.find_all('a')

    assert normalize_spaces(nav_links[0].text) == '2010 to 2011 financial year'
    assert normalize_spaces(nav.find('li', {'aria-selected': 'true'}).text) == '2011 to 2012 financial year'
    assert normalize_spaces(nav_links[1].text) == '2012 to 2013 financial year'
    assert '252,190' in cols[1].text
    assert 'Text messages' in cols[1].text

    table = page.find('table').text.strip()

    assert '249,860 free text messages' in table
    assert '40 free text messages' in table
    assert '960 text messages at 1.65p' in table
    assert 'April' in table
    assert 'February' in table
    assert 'March' in table
    assert '£20.59' in table
    assert '140 free text messages' in table
    assert '£20.30' in table
    assert '1,230 text messages at 1.65p' in table
    assert '10 second class letters at 31p' in normalize_spaces(table)
    assert '5 first class letters at 33p' in normalize_spaces(table)


@freeze_time("2012-04-30 12:12:12")
def test_usage_page_displays_letters_ordered_by_postage(
    mocker,
    logged_in_client,
    service_one,
    mock_get_usage,
    mock_get_free_sms_fragment_limit
):
    billable_units_resp = [
        {'month': 'April', 'notification_type': 'letter', 'rate': 0.5, 'billing_units': 1, 'postage': 'second'},
        {'month': 'April', 'notification_type': 'letter', 'rate': 0.3, 'billing_units': 3, 'postage': 'second'},
        {'month': 'April', 'notification_type': 'letter', 'rate': 0.5, 'billing_units': 1, 'postage': 'first'},
    ]
    mocker.patch('app.billing_api_client.get_billable_units_ft', return_value=billable_units_resp)
    service_one['permissions'].append('letter')
    response = logged_in_client.get(url_for('main.usage', service_id=SERVICE_ONE_ID))

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    row_for_april = page.find('table').find('tr', class_='table-row')
    postage_details = row_for_april.find_all('li', class_='tabular-numbers')

    assert len(postage_details) == 3
    assert normalize_spaces(postage_details[0].text) == '1 first class letter at 50p'
    assert normalize_spaces(postage_details[1].text) == '3 second class letters at 30p'
    assert normalize_spaces(postage_details[2].text) == '1 second class letter at 50p'


def test_usage_page_with_year_argument(
    logged_in_client,
    mock_get_usage,
    mock_get_billable_units,
    mock_get_free_sms_fragment_limit,
):
    assert logged_in_client.get(url_for('main.usage', service_id=SERVICE_ONE_ID, year=2000)).status_code == 200
    mock_get_billable_units.assert_called_once_with(SERVICE_ONE_ID, 2000)
    mock_get_usage.assert_called_once_with(SERVICE_ONE_ID, 2000)
    mock_get_free_sms_fragment_limit.assert_called_with(SERVICE_ONE_ID, 2000)


def test_usage_page_for_invalid_year(
    logged_in_client,
):
    assert logged_in_client.get(url_for('main.usage', service_id=SERVICE_ONE_ID, year='abcd')).status_code == 404


@freeze_time("2012-03-31 12:12:12")
def test_future_usage_page(
    logged_in_client,
    mock_get_future_usage,
    mock_get_future_billable_units,
    mock_get_free_sms_fragment_limit
):
    assert logged_in_client.get(url_for('main.usage', service_id=SERVICE_ONE_ID, year=2014)).status_code == 200

    mock_get_future_billable_units.assert_called_once_with(SERVICE_ONE_ID, 2014)
    mock_get_future_usage.assert_called_once_with(SERVICE_ONE_ID, 2014)
    mock_get_free_sms_fragment_limit.assert_called_with(SERVICE_ONE_ID, 2014)


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


def test_menu_send_messages(
    mocker,
    app_,
    api_user_active,
    service_one,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_template_statistics,
    mock_get_service_statistics,
    mock_get_usage,
    mock_get_inbound_sms_summary,
    mock_get_free_sms_fragment_limit,
):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['view_activity', 'send_messages'])
        page = resp.get_data(as_text=True)
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
        ) in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page

        assert url_for('main.service_settings', service_id=service_one['id']) not in page
        assert url_for('main.api_keys', service_id=service_one['id']) not in page
        assert url_for('main.view_providers') not in page


def test_menu_manage_service(
    mocker,
    app_,
    api_user_active,
    service_one,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_template_statistics,
    mock_get_service_statistics,
    mock_get_usage,
    mock_get_inbound_sms_summary,
    mock_get_free_sms_fragment_limit,
):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['view_activity', 'manage_templates', 'manage_service'])
        page = resp.get_data(as_text=True)
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
        ) in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page
        assert url_for('main.service_settings', service_id=service_one['id']) in page

        assert url_for('main.api_keys', service_id=service_one['id']) not in page


def test_menu_manage_api_keys(
    mocker,
    app_,
    api_user_active,
    service_one,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_template_statistics,
    mock_get_service_statistics,
    mock_get_usage,
    mock_get_inbound_sms_summary,
    mock_get_free_sms_fragment_limit,
):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['view_activity', 'manage_api_keys'])

        page = resp.get_data(as_text=True)

        assert url_for('main.choose_template', service_id=service_one['id'],) in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page
        assert url_for('main.service_settings', service_id=service_one['id']) in page
        assert url_for('main.api_integration', service_id=service_one['id']) in page


def test_menu_all_services_for_platform_admin_user(
    mocker,
    app_,
    platform_admin_user,
    service_one,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_template_statistics,
    mock_get_service_statistics,
    mock_get_usage,
    mock_get_inbound_sms_summary,
    mock_get_free_sms_fragment_limit,
):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            platform_admin_user,
            service_one,
            [])
        page = resp.get_data(as_text=True)
        assert url_for('main.choose_template', service_id=service_one['id']) in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page
        assert url_for('main.service_settings', service_id=service_one['id']) in page
        assert url_for('main.view_notifications', service_id=service_one['id'], message_type='email') in page
        assert url_for('main.view_notifications', service_id=service_one['id'], message_type='sms') in page
        assert url_for('main.api_keys', service_id=service_one['id']) not in page


def test_route_for_service_permissions(
    mocker,
    app_,
    api_user_active,
    service_one,
    mock_get_service,
    mock_get_user,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_template_statistics,
    mock_get_service_statistics,
    mock_get_usage,
    mock_get_inbound_sms_summary
):
    with app_.test_request_context():
        validate_route_permission(
            mocker,
            app_,
            "GET",
            200,
            url_for('main.service_dashboard', service_id=service_one['id']),
            ['view_activity'],
            api_user_active,
            service_one)


def test_aggregate_template_stats():
    from app.main.views.dashboard import aggregate_usage
    expected = aggregate_usage(copy.deepcopy(stub_template_stats))

    assert len(expected) == 4
    assert expected[0]['template_name'] == 'four'
    assert expected[0]['count'] == 400
    assert expected[0]['template_id'] == 'id-4'
    assert expected[0]['template_type'] == 'letter'
    assert expected[1]['template_name'] == 'three'
    assert expected[1]['count'] == 300
    assert expected[1]['template_id'] == 'id-3'
    assert expected[1]['template_type'] == 'letter'
    assert expected[2]['template_name'] == 'two'
    assert expected[2]['count'] == 200
    assert expected[2]['template_id'] == 'id-2'
    assert expected[2]['template_type'] == 'email'
    assert expected[3]['template_name'] == 'one'
    assert expected[3]['count'] == 100
    assert expected[3]['template_id'] == 'id-1'
    assert expected[3]['template_type'] == 'sms'


def test_service_dashboard_updates_gets_dashboard_totals(
    mocker,
    logged_in_client,
    mock_get_service_templates,
    mock_get_template_statistics,
    mock_get_service_statistics,
    mock_get_jobs,
    mock_get_usage,
    mock_get_inbound_sms_summary
):
    mocker.patch('app.main.views.dashboard.get_dashboard_totals', return_value={
        'email': {'requested': 123, 'delivered': 0, 'failed': 0},
        'sms': {'requested': 456, 'delivered': 0, 'failed': 0}
    })

    response = logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    numbers = [number.text.strip() for number in page.find_all('div', class_='big-number-number')]
    assert '123' in numbers
    assert '456' in numbers


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


def test_format_monthly_stats_empty_case():
    assert format_monthly_stats_to_list({}) == []


def test_format_monthly_stats_labels_month():
    resp = format_monthly_stats_to_list({'2016-07': {}})
    assert resp[0]['name'] == 'July'


def test_format_monthly_stats_has_stats_with_failure_rate():
    resp = format_monthly_stats_to_list({
        '2016-07': {'sms': _stats(3, 1, 2)}
    })
    assert resp[0]['sms_counts'] == {
        'failed': 2,
        'failed_percentage': '66.7',
        'requested': 3,
        'show_warning': True,
    }


def test_format_monthly_stats_works_for_email_letter():
    resp = format_monthly_stats_to_list({
        '2016-07': {
            'sms': {},
            'email': {},
            'letter': {},
        }
    })
    assert isinstance(resp[0]['sms_counts'], dict)
    assert isinstance(resp[0]['email_counts'], dict)
    assert isinstance(resp[0]['letter_counts'], dict)


def _stats(requested, delivered, failed):
    return {'requested': requested, 'delivered': delivered, 'failed': failed}


@pytest.mark.parametrize('dict_in, expected_failed, expected_requested', [
    (
        {},
        0,
        0
    ),
    (
        {'temporary-failure': 1, 'permanent-failure': 1, 'technical-failure': 1},
        3,
        3,
    ),
    (
        {'created': 1, 'pending': 1, 'sending': 1, 'delivered': 1},
        0,
        4,
    ),
])
def test_aggregate_status_types(dict_in, expected_failed, expected_requested):
    sms_counts = aggregate_status_types({'sms': dict_in})['sms_counts']
    assert sms_counts['failed'] == expected_failed
    assert sms_counts['requested'] == expected_requested


@pytest.mark.parametrize(
    'now, expected_number_of_months', [
        (freeze_time("2017-12-31 11:09:00.061258"), 12),
        (freeze_time("2017-01-01 11:09:00.061258"), 10)
    ]
)
def test_get_free_paid_breakdown_for_billable_units(now, expected_number_of_months):
    sms_allowance = 250000
    with now:
        billing_units = get_free_paid_breakdown_for_billable_units(
            2016, sms_allowance, [
                {
                    'month': 'April', 'international': False, 'rate_multiplier': 1,
                    'notification_type': 'sms', 'rate': 1.65, 'billing_units': 100000
                },
                {
                    'month': 'May', 'international': False, 'rate_multiplier': 1,
                    'notification_type': 'sms', 'rate': 1.65, 'billing_units': 100000
                },
                {
                    'month': 'June', 'international': False, 'rate_multiplier': 1,
                    'notification_type': 'sms', 'rate': 1.65, 'billing_units': 100000
                },
                {
                    'month': 'February', 'international': False, 'rate_multiplier': 1,
                    'notification_type': 'sms', 'rate': 1.65, 'billing_units': 2000
                },
            ]
        )
        assert list(billing_units) == [
            {'free': 100000, 'name': 'April', 'paid': 0, 'letter_total': 0, 'letters': [], 'letter_cumulative': 0},
            {'free': 100000, 'name': 'May', 'paid': 0, 'letter_total': 0, 'letters': [], 'letter_cumulative': 0},
            {'free': 50000, 'name': 'June', 'paid': 50000, 'letter_total': 0, 'letters': [], 'letter_cumulative': 0},
            {'free': 0, 'name': 'July', 'paid': 0, 'letter_total': 0, 'letters': [], 'letter_cumulative': 0},
            {'free': 0, 'name': 'August', 'paid': 0, 'letter_total': 0, 'letters': [], 'letter_cumulative': 0},
            {'free': 0, 'name': 'September', 'paid': 0, 'letter_total': 0, 'letters': [], 'letter_cumulative': 0},
            {'free': 0, 'name': 'October', 'paid': 0, 'letter_total': 0, 'letters': [], 'letter_cumulative': 0},
            {'free': 0, 'name': 'November', 'paid': 0, 'letter_total': 0, 'letters': [], 'letter_cumulative': 0},
            {'free': 0, 'name': 'December', 'paid': 0, 'letter_total': 0, 'letters': [], 'letter_cumulative': 0},
            {'free': 0, 'name': 'January', 'paid': 0, 'letter_total': 0, 'letters': [], 'letter_cumulative': 0},
            {'free': 0, 'name': 'February', 'paid': 2000, 'letter_total': 0, 'letters': [], 'letter_cumulative': 0},
            {'free': 0, 'name': 'March', 'paid': 0, 'letter_total': 0, 'letters': [], 'letter_cumulative': 0}
        ][:expected_number_of_months]


def test_format_template_stats_to_list_with_no_stats():
    assert list(format_template_stats_to_list({})) == []


def test_format_template_stats_to_list():
    counts = {
        'created': 1,
        'pending': 1,
        'delivered': 1,
        'failed': 1,
        'temporary-failure': 1,
        'permanent-failure': 1,
        'technical-failure': 1,
        'do-not-count': 999,
    }
    stats_list = list(format_template_stats_to_list({
        'template_2_id': {
            'counts': {},
            'name': 'bar',
        },
        'template_1_id': {
            'counts': counts,
            'name': 'foo',
        },
    }))

    # we don’t care about the order of this function’s output
    assert len(stats_list) == 2
    assert {
        'counts': counts,
        'name': 'foo',
        'requested_count': 7,
        'id': 'template_1_id',
    } in stats_list
    assert {
        'counts': {},
        'name': 'bar',
        'requested_count': 0,
        'id': 'template_2_id',
    } in stats_list


def test_get_tuples_of_financial_years():
    assert list(get_tuples_of_financial_years(
        lambda year: 'http://example.com?year={}'.format(year),
        start=2040,
        end=2041,
    )) == [
        ('financial year', 2040, 'http://example.com?year=2040', '2040 to 2041'),
        ('financial year', 2041, 'http://example.com?year=2041', '2041 to 2042'),
    ]


def test_get_tuples_of_financial_years_defaults_to_2015():
    assert 2015 in list(get_tuples_of_financial_years(
        lambda year: 'http://example.com?year={}'.format(year),
        end=2040,
    ))[0]


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_all_jobs_with_valid_statuses(
    logged_in_client,
    mock_get_template_statistics,
    mock_get_service_statistics,
    mock_get_service_templates_when_no_templates_exist,
    mock_get_jobs,
    mock_get_usage,
    mock_get_inbound_sms_summary
):
    logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    first_call = mock_get_jobs.call_args_list[0]
    # first call - checking for any jobs
    assert first_call == call(SERVICE_ONE_ID)
    second_call = mock_get_jobs.call_args_list[1]
    # second call - scheduled jobs only
    assert second_call == call(SERVICE_ONE_ID, statuses=['scheduled'])
    # third call - everything but scheduled and cancelled
    third_call = mock_get_jobs.call_args_list[2]
    assert third_call == call(SERVICE_ONE_ID, limit_days=7, statuses={
        'pending',
        'in progress',
        'finished',
        'sending limits exceeded',
        'ready to send',
        'sent to dvla'
    })
