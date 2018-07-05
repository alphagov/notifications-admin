import json
import uuid
from urllib.parse import parse_qs, quote, urlparse

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from freezegun import freeze_time

from app.main.views.jobs import get_status_filters, get_time_left
from tests.conftest import (
    SERVICE_ONE_ID,
    active_caseworking_user,
    active_user_view_permissions,
    mock_get_notifications,
    normalize_spaces,
)


@pytest.mark.parametrize('user', (
    active_user_view_permissions,
    active_caseworking_user,
))
@pytest.mark.parametrize(
    "message_type,page_title", [
        ('email', 'Emails'),
        ('sms', 'Text messages')
    ]
)
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
@pytest.mark.parametrize(
    "page_argument, expected_page_argument", [
        (1, 1),
        (22, 22),
        (None, 1)
    ]
)
@pytest.mark.parametrize(
    "to_argument, expected_to_argument", [
        ('', ''),
        ('+447900900123', '+447900900123'),
        ('test@example.com', 'test@example.com'),
    ]
)
def test_can_show_notifications(
    logged_in_client,
    service_one,
    mock_get_notifications,
    mock_get_service_statistics,
    message_type,
    page_title,
    status_argument,
    expected_api_call,
    page_argument,
    expected_page_argument,
    to_argument,
    expected_to_argument,
    mocker,
    user,
    fake_uuid,
):
    mocker.patch('app.user_api_client.get_user', return_value=user(fake_uuid))
    if expected_to_argument:
        response = logged_in_client.post(
            url_for(
                'main.view_notifications',
                service_id=service_one['id'],
                message_type=message_type,
                status=status_argument,
                page=page_argument,
            ),
            data={
                'to': to_argument
            }
        )
    else:
        response = logged_in_client.get(url_for(
            'main.view_notifications',
            service_id=service_one['id'],
            message_type=message_type,
            status=status_argument,
            page=page_argument,
        ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    text_of_first_row = page.select('tbody tr')[0].text
    assert '07123456789' in text_of_first_row
    assert (
        'template content' in text_of_first_row or
        'template subject' in text_of_first_row
    )
    assert 'Delivered' in text_of_first_row
    assert page_title in page.h1.text.strip()

    path_to_json = page.find("div", {'data-key': 'notifications'})['data-resource']

    url = urlparse(path_to_json)
    assert url.path == '/services/{}/notifications/{}.json'.format(service_one['id'], message_type)
    query_dict = parse_qs(url.query)
    if status_argument:
        assert query_dict['status'] == [status_argument]
    if expected_page_argument:
        assert query_dict['page'] == [str(expected_page_argument)]
    assert 'to' not in query_dict

    mock_get_notifications.assert_called_with(
        limit_days=7,
        page=expected_page_argument,
        service_id=service_one['id'],
        status=expected_api_call,
        template_type=[message_type],
        to=expected_to_argument,
    )

    json_response = logged_in_client.get(url_for(
        'main.get_notifications_as_json',
        service_id=service_one['id'],
        message_type=message_type,
        status=status_argument
    ))
    json_content = json.loads(json_response.get_data(as_text=True))
    assert json_content.keys() == {'counts', 'notifications'}


def test_letters_with_status_virus_scan_failed_shows_a_failure_description(
    mocker,
    active_user_with_permissions,
    logged_in_client,
    service_one,
    mock_get_service_statistics,
):
    mock_get_notifications(
        mocker,
        active_user_with_permissions,
        is_precompiled_letter=True,
        noti_status='virus-scan-failed'
    )
    response = logged_in_client.get(url_for(
        'main.view_notifications',
        service_id=service_one['id'],
        message_type='letter',
        status='',
    ))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    error_description = page.find('div', attrs={'class': 'table-field-status-error'}).text.strip()
    assert 'Virus detected\n' in error_description


@pytest.mark.parametrize('letter_status', [
    'pending-virus-check', 'virus-scan-failed'
])
def test_should_not_show_preview_link_for_precompiled_letters_in_virus_states(
    mocker,
    active_user_with_permissions,
    logged_in_client,
    service_one,
    mock_get_service_statistics,
    letter_status,
):
    mock_get_notifications(
        mocker,
        active_user_with_permissions,
        is_precompiled_letter=True,
        noti_status=letter_status
    )
    response = logged_in_client.get(url_for(
        'main.view_notifications',
        service_id=service_one['id'],
        message_type='letter',
        status='',
    ))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert not page.find('a', attrs={'class': 'file-list-filename'})


def test_shows_message_when_no_notifications(
    client_request,
    mock_get_service_statistics,
    mock_get_notifications_with_no_notifications,
):

    page = client_request.get(
        'main.view_notifications',
        service_id=SERVICE_ONE_ID,
        message_type='sms',
    )

    assert normalize_spaces(page.select('tbody tr')[0].text) == (
        'No messages found'
    )


@pytest.mark.parametrize((
    'initial_query_arguments,'
    'form_post_data,'
    'expected_search_box_contents'
), [
    (
        {
            'message_type': 'sms',
        },
        {},
        '',
    ),
    (
        {
            'message_type': 'sms',
        },
        {
            'to': '+33(0)5-12-34-56-78',
        },
        '+33(0)5-12-34-56-78',
    ),
    (
        {
            'status': 'failed',
            'message_type': 'email',
            'page': '99',
        },
        {
            'to': 'test@example.com',
        },
        'test@example.com',
    ),
])
def test_search_recipient_form(
    logged_in_client,
    mock_get_notifications,
    mock_get_service_statistics,
    initial_query_arguments,
    form_post_data,
    expected_search_box_contents,
):
    response = logged_in_client.post(
        url_for(
            'main.view_notifications',
            service_id=SERVICE_ONE_ID,
            **initial_query_arguments
        ),
        data=form_post_data
    )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.find("form")['method'] == 'post'
    action_url = page.find("form")['action']
    url = urlparse(action_url)
    assert url.path == '/services/{}/notifications/{}'.format(
        SERVICE_ONE_ID,
        initial_query_arguments['message_type']
    )
    query_dict = parse_qs(url.query)
    assert query_dict == {}

    recipient_inputs = page.select("input[name=to]")
    assert(len(recipient_inputs) == 2)

    for field in recipient_inputs:
        assert field['value'] == expected_search_box_contents


def test_should_show_notifications_for_a_service_with_next_previous(
    logged_in_client,
    service_one,
    active_user_with_permissions,
    mock_get_notifications_with_previous_next,
    mock_get_service_statistics,
    mocker,
):
    response = logged_in_client.get(url_for(
        'main.view_notifications',
        service_id=service_one['id'],
        message_type='sms',
        page=2
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    next_page_link = page.find('a', {'rel': 'next'})
    prev_page_link = page.find('a', {'rel': 'previous'})
    assert (
        url_for('main.view_notifications', service_id=service_one['id'], message_type='sms', page=3) in
        next_page_link['href']
    )
    assert 'Next page' in next_page_link.text.strip()
    assert 'page 3' in next_page_link.text.strip()
    assert (
        url_for('main.view_notifications', service_id=service_one['id'], message_type='sms', page=1) in
        prev_page_link['href']
    )
    assert 'Previous page' in prev_page_link.text.strip()
    assert 'page 1' in prev_page_link.text.strip()


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


STATISTICS = {
    'sms': {
        'requested': 6,
        'failed': 2,
        'delivered': 1
    }
}


def test_get_status_filters_calculates_stats(client):
    ret = get_status_filters({'id': 'foo'}, 'sms', STATISTICS)

    assert {label: count for label, _option, _link, count in ret} == {
        'total': 6,
        'sending': 3,
        'failed': 2,
        'delivered': 1
    }


def test_get_status_filters_in_right_order(client):
    ret = get_status_filters({'id': 'foo'}, 'sms', STATISTICS)

    assert [label for label, _option, _link, _count in ret] == [
        'total', 'sending', 'delivered', 'failed'
    ]


def test_get_status_filters_constructs_links(client):
    ret = get_status_filters({'id': 'foo'}, 'sms', STATISTICS)

    link = ret[0][2]
    assert link == '/services/foo/notifications/sms?status={}'.format(quote('sending,delivered,failed'))


def test_html_contains_notification_id(
    logged_in_client,
    service_one,
    active_user_with_permissions,
    mock_get_notifications,
    mock_get_service_statistics,
    mocker,
):
    response = logged_in_client.get(url_for(
        'main.view_notifications',
        service_id=service_one['id'],
        message_type='sms',
        status='')
    )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    notifications = page.tbody.find_all('tr')
    for tr in notifications:
        assert uuid.UUID(tr.attrs['id'])


def test_redacts_templates_that_should_be_redacted(
    client_request,
    mocker,
    active_user_with_permissions,
    mock_get_service_statistics,
):
    mock_get_notifications(
        mocker,
        active_user_with_permissions,
        template_content="hello ((name))",
        personalisation={'name': 'Jo'},
        redact_personalisation=True,
    )
    page = client_request.get(
        'main.view_notifications',
        service_id=SERVICE_ONE_ID,
        message_type='sms',
    )

    assert normalize_spaces(page.select('tbody tr th')[0].text) == (
        '07123456789 hello hidden'
    )


@pytest.mark.parametrize(
    "message_type, tablist_visible, search_bar_visible", [
        ('email', True, True),
        ('sms', True, True),
        ('letter', False, False)
    ]
)
def test_big_numbers_and_search_dont_show_for_letters(
    client_request,
    service_one,
    mock_get_notifications,
    active_user_with_permissions,
    mock_get_service_statistics,
    message_type,
    tablist_visible,
    search_bar_visible
):
    page = client_request.get(
        'main.view_notifications',
        service_id=service_one['id'],
        message_type=message_type,
        status='',
        page=1,
    )

    assert (len(page.select("[role=tablist]")) > 0) == tablist_visible
    assert (len(page.select("[type=search]")) > 0) == search_bar_visible


@freeze_time("2017-09-27 16:30:00.000000")
@pytest.mark.parametrize(
    "message_type, hint_status_visible", [
        ('email', True),
        ('sms', True),
        ('letter', False)
    ]
)
def test_sending_status_hint_does_not_include_status_for_letters(
    client_request,
    service_one,
    active_user_with_permissions,
    mock_get_service_statistics,
    message_type,
    hint_status_visible,
    mocker
):
    mock_get_notifications(mocker, True, diff_template_type=message_type)

    page = client_request.get(
        'main.view_notifications',
        service_id=service_one['id'],
        message_type=message_type
    )

    if message_type == 'letter':
        assert normalize_spaces(page.select(".align-with-message-body")[0].text) == "27 September at 5:30pm"
    else:
        assert normalize_spaces(page.select(".align-with-message-body")[0].text) == "Delivered 27 September at 5:31pm"


@pytest.mark.parametrize("is_precompiled_letter,expected_hint", [
    (True, "Provided as PDF"),
    (False, "template subject")
])
def test_should_expected_hint_for_letters(
    logged_in_client,
    service_one,
    active_user_with_permissions,
    mock_get_service_statistics,
    mocker,
    fake_uuid,
    is_precompiled_letter,
    expected_hint
):
    mock_get_notifications(
        mocker, active_user_with_permissions, is_precompiled_letter=is_precompiled_letter)

    response = logged_in_client.get(url_for(
        'main.view_notifications',
        service_id=SERVICE_ONE_ID,
        message_type='letter'
    ))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('p', {'class': 'file-list-hint'}).text.strip() == expected_hint
