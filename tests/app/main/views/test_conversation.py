from datetime import datetime
import json
import pytest

from flask import (
    url_for,
)
from notifications_python_client.errors import HTTPError
from freezegun import freeze_time

from tests.conftest import (
    SERVICE_ONE_ID,
    normalize_spaces,
    mock_get_notifications,
)
from app.main.views.conversation import get_user_number


def test_get_user_phone_number_when_only_inbound_exists(mocker):

    mock_get_inbound_sms = mocker.patch(
        'app.main.views.conversation.service_api_client.get_inbound_sms_by_id',
        return_value={
            'user_number': '4407900900123',
            'notify_number': '07900000002'
        }
    )
    mock_get_notification = mocker.patch(
        'app.main.views.conversation.notification_api_client.get_notification',
        side_effect=HTTPError,
    )
    assert get_user_number('service', 'notification') == '07900 900123'
    mock_get_inbound_sms.assert_called_once_with('service', 'notification')
    assert mock_get_notification.called is False


def test_get_user_phone_number_when_only_outbound_exists(mocker):
    mock_get_inbound_sms = mocker.patch(
        'app.main.views.conversation.service_api_client.get_inbound_sms_by_id',
        side_effect=HTTPError,
    )
    mock_get_notification = mocker.patch(
        'app.main.views.conversation.notification_api_client.get_notification',
        return_value={
            'to': '15550000000'
        }
    )
    assert get_user_number('service', 'notification') == '+1 555-000-0000'
    mock_get_inbound_sms.assert_called_once_with('service', 'notification')
    mock_get_notification.assert_called_once_with('service', 'notification')


def test_get_user_phone_number_raises_if_both_api_requests_fail(mocker):
    mock_get_inbound_sms = mocker.patch(
        'app.main.views.conversation.service_api_client.get_inbound_sms_by_id',
        side_effect=HTTPError,
    )
    mock_get_notification = mocker.patch(
        'app.main.views.conversation.notification_api_client.get_notification',
        side_effect=HTTPError,
    )
    with pytest.raises(HTTPError):
        get_user_number('service', 'notification')
    mock_get_inbound_sms.assert_called_once_with('service', 'notification')
    mock_get_notification.assert_called_once_with('service', 'notification')


@pytest.mark.parametrize('outbound_redacted, expected_outbound_content', [
    (True, 'Hello hidden'),
    (False, 'Hello Jo'),
])
@freeze_time("2012-01-01 00:00:00")
def test_view_conversation(
    client_request,
    mocker,
    api_user_active,
    mock_get_notification,
    fake_uuid,
    outbound_redacted,
    expected_outbound_content,
    mock_get_inbound_sms
):

    mock_get_notifications(
        mocker,
        api_user_active,
        template_content='Hello ((name))',
        personalisation={'name': 'Jo'},
        redact_personalisation=outbound_redacted,
    )

    page = client_request.get(
        'main.conversation',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    messages = page.select('.sms-message-wrapper')
    statuses = page.select('.sms-message-status')

    assert len(messages) == 13
    assert len(statuses) == 13

    for index, expected in enumerate([
        (
            'message-8',
            'yesterday at 2:59pm',
        ),
        (
            'message-7',
            'yesterday at 2:59pm',
        ),
        (
            'message-6',
            'yesterday at 4:59pm',
        ),
        (
            'message-5',
            'yesterday at 6:59pm',
        ),
        (
            'message-4',
            'yesterday at 8:59pm',
        ),
        (
            'message-3',
            'yesterday at 10:59pm',
        ),
        (
            'message-2',
            'yesterday at 10:59pm',
        ),
        (
            'message-1',
            'yesterday at 11:00pm',
        ),
        (
            expected_outbound_content,
            'yesterday at midnight',
        ),
        (
            expected_outbound_content,
            'yesterday at midnight',
        ),
        (
            expected_outbound_content,
            'yesterday at midnight',
        ),
        (
            expected_outbound_content,
            'yesterday at midnight',
        ),
        (
            expected_outbound_content,
            'yesterday at midnight',
        ),
    ]):
        assert (
            normalize_spaces(messages[index].text),
            normalize_spaces(statuses[index].text),
        ) == expected


def test_escaped_characters_in_inbound_messages(
    client_request,
    mock_get_notification,
    mock_get_notifications,
    mock_get_inbound_sms_with_special_characters,
    fake_uuid,
):

    page = client_request.get(
        'main.conversation',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert normalize_spaces(
        str(page.select_one('.sms-message-inbound .sms-message-wrapper'))
    ) == (
        "<div class=\"sms-message-wrapper\"> "
        "the first line's content<br/>the second line's content<br/>a fire truck 🚒 "
        "</div>"
    )


def test_view_conversation_updates(
    logged_in_client,
    mocker,
    fake_uuid,
    mock_get_notification,
):

    mock_get_partials = mocker.patch(
        'app.main.views.conversation.get_conversation_partials',
        return_value={'messages': 'foo'}
    )

    response = logged_in_client.get(url_for(
        'main.conversation_updates',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    ))

    assert response.status_code == 200
    assert json.loads(response.get_data(as_text=True)) == {'messages': 'foo'}

    mock_get_partials.assert_called_once_with(SERVICE_ONE_ID, '07123 456789')


@freeze_time("2012-01-01 00:00:00")
def test_view_conversation_with_empty_inbound(
    client_request,
    mocker,
    api_user_active,
    mock_get_notification,
    mock_get_notifications_with_no_notifications,
    fake_uuid
):
    mock_get_inbound_sms = mocker.patch(
        'app.main.views.conversation.service_api_client.get_inbound_sms',
        return_value=[{
            'user_number': '07900000001',
            'notify_number': '07900000002',
            'content': '',
            'created_at': datetime.utcnow().isoformat(),
            'id': fake_uuid
        }]
    )

    page = client_request.get(
        'main.conversation',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    messages = page.select('.sms-message-wrapper')
    assert len(messages) == 1
    assert mock_get_inbound_sms.called is True


def test_conversation_links_to_reply(
    client_request,
    fake_uuid,
    mock_get_notification,
    mock_get_notifications,
    mock_get_inbound_sms,
):
    page = client_request.get(
        'main.conversation',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert page.select('main p')[-1].select_one('a')['href'] == (
        url_for(
            '.conversation_reply',
            service_id=SERVICE_ONE_ID,
            notification_id=fake_uuid,
        )
    )


def test_conversation_reply_shows_templates(
    client_request,
    fake_uuid,
    mock_get_service_templates,
):
    page = client_request.get(
        'main.conversation_reply',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    for index, expected in enumerate([
        'sms_template_one',
        'sms_template_two',
    ]):
        link = page.select('.message-name')[index]
        assert normalize_spaces(link.text) == expected
        assert link.select_one('a')['href'].startswith(
            url_for(
                'main.conversation_reply_with_template',
                service_id=SERVICE_ONE_ID,
                notification_id=fake_uuid,
                template_id='',
            )
        )


def test_conversation_reply_redirects_with_phone_number_from_notification(
    client_request,
    fake_uuid,
    mock_get_notification,
    mock_get_service_template,
):

    page = client_request.get(
        'main.conversation_reply_with_template',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        template_id=fake_uuid,
        _follow_redirects=True,
    )

    for element, expected_text in [
        ('h1', 'Preview of Two week reminder'),
        ('.sms-message-recipient', 'To: 07123 456789'),
        ('.sms-message-wrapper', 'service one: Template <em>content</em> with & entity'),
    ]:
        assert normalize_spaces(page.select_one(element).text) == expected_text
