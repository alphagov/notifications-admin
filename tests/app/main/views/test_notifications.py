from freezegun import freeze_time
from flask import url_for
import pytest

from notifications_utils.template import LetterImageTemplate
from tests.conftest import mock_get_notification, SERVICE_ONE_ID, normalize_spaces


@pytest.mark.parametrize('notification_status, expected_status', [
    ('created', 'Sending'),
    ('sending', 'Sending'),
    ('delivered', 'Delivered'),
    ('failed', 'Failed'),
    ('temporary-failure', 'Phone not accepting messages right now'),
    ('permanent-failure', 'Phone number doesn’t exist'),
    ('technical-failure', 'Technical failure'),
])
@freeze_time("2016-01-01 11:09:00.061258")
def test_notification_status_page_shows_details(
    client_request,
    mocker,
    service_one,
    fake_uuid,
    notification_status,
    expected_status,
):

    _mock_get_notification = mock_get_notification(
        mocker,
        fake_uuid,
        notification_status=notification_status
    )

    page = client_request.get(
        'main.view_notification',
        service_id=service_one['id'],
        notification_id=fake_uuid
    )

    assert normalize_spaces(page.select('.sms-message-recipient')[0].text) == (
        'To: 07123456789'
    )
    assert normalize_spaces(page.select('.sms-message-wrapper')[0].text) == (
        'service one: hello Jo'
    )
    assert normalize_spaces(page.select('.ajax-block-container p')[0].text) == (
        expected_status
    )

    _mock_get_notification.assert_called_with(
        service_one['id'],
        fake_uuid
    )


@pytest.mark.parametrize('template_redaction_setting, expected_content', [
    (False, 'service one: hello Jo'),
    (True, 'service one: hello hidden'),
])
@freeze_time("2016-01-01 11:09:00.061258")
def test_notification_status_page_respects_redaction(
    client_request,
    mocker,
    service_one,
    fake_uuid,
    template_redaction_setting,
    expected_content,
):

    _mock_get_notification = mock_get_notification(
        mocker,
        fake_uuid,
        redact_personalisation=template_redaction_setting,
    )

    page = client_request.get(
        'main.view_notification',
        service_id=service_one['id'],
        notification_id=fake_uuid
    )

    assert normalize_spaces(page.select('.sms-message-wrapper')[0].text) == expected_content

    _mock_get_notification.assert_called_with(
        service_one['id'],
        fake_uuid,
    )


@freeze_time("2012-01-01 01:01")
def test_notification_page_doesnt_link_to_template_in_tour(
    client_request,
    fake_uuid,
    mock_get_notification,
):

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        help=3,
    )

    assert normalize_spaces(page.select('main p:nth-of-type(1)')[0].text) == (
        'sample template sent by Test User on 1 January at 1:01am'
    )
    assert len(page.select('main p:nth-of-type(1) a')) == 0


@freeze_time("2016-01-01 01:01")
def test_notification_page_shows_status_of_letter_notification(
    client_request,
    mocker,
    fake_uuid,
):

    mock_get_notification(mocker, fake_uuid, template_type='letter')

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert normalize_spaces(page.select('main p:nth-of-type(1)')[0].text) == (
        'sample template sent by Test User on 1 January at 1:01am'
    )
    assert normalize_spaces(page.select('main p:nth-of-type(2)')[0].text) == (
        'Estimated delivery date: 6 January'
    )
    assert page.select('p.notification-status') == []


def test_should_show_image_of_letter_notification(
    logged_in_client,
    fake_uuid,
    mocker
):

    mock_get_notification(mocker, fake_uuid, template_type='letter')

    mocked_preview = mocker.patch(
        'app.main.views.templates.TemplatePreview.from_utils_template',
        return_value='foo'
    )

    response = logged_in_client.get(url_for(
        'main.view_letter_notification_as_image',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    ))

    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'foo'
    assert isinstance(mocked_preview.call_args[0][0], LetterImageTemplate)
    assert mocked_preview.call_args[0][1] == 'png'


@pytest.mark.parametrize('service_permissions, template_type, link_expected', [
    ([], '', False),
    (['inbound_sms'], 'email', False),
    (['inbound_sms'], 'letter', False),
    (['inbound_sms'], 'sms', True),
])
def test_notification_page_has_link_to_send_another_for_sms(
    client_request,
    mocker,
    fake_uuid,
    service_one,
    service_permissions,
    template_type,
    link_expected,
):

    service_one['permissions'] = service_permissions
    mock_get_notification(mocker, fake_uuid, template_type=template_type)

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    last_paragraph = page.select('main p')[-1]

    if link_expected:
        assert normalize_spaces(last_paragraph.text) == (
            'See all text messages sent to this phone number'
        )
        assert last_paragraph.select_one('a')['href'] == url_for(
            '.conversation',
            service_id=SERVICE_ONE_ID,
            notification_id=fake_uuid,
            _anchor='n{}'.format(fake_uuid),
        )
    else:
        # covers ‘Delivered’, ‘Expected delivery date’
        assert 'deliver' in normalize_spaces(last_paragraph.text).lower()
