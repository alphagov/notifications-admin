import base64
from datetime import datetime
from functools import partial
from unittest.mock import mock_open

import pytest
from flask import url_for
from freezegun import freeze_time
from notifications_python_client.errors import APIError
from PyPDF2.utils import PdfReadError

from tests.conftest import (
    SERVICE_ONE_ID,
    active_caseworking_user,
    active_user_with_permissions,
    mock_get_notification,
    normalize_spaces,
)


@pytest.mark.parametrize('key_type, notification_status, expected_status', [
    (None, 'created', 'Sending'),
    (None, 'sending', 'Sending'),
    (None, 'delivered', 'Delivered'),
    (None, 'failed', 'Failed'),
    (None, 'temporary-failure', 'Phone not accepting messages right now'),
    (None, 'permanent-failure', 'Phone number does not exist'),
    (None, 'technical-failure', 'Technical failure'),
    ('team', 'delivered', 'Delivered'),
    ('live', 'delivered', 'Delivered'),
    ('test', 'sending', 'Sending (test)'),
    ('test', 'delivered', 'Delivered (test)'),
    ('test', 'permanent-failure', 'Phone number does not exist (test)'),
])
@pytest.mark.parametrize('user', [
    active_user_with_permissions,
    active_caseworking_user,
])
@freeze_time("2016-01-01 11:09:00.061258")
def test_notification_status_page_shows_details(
    client_request,
    mocker,
    mock_has_no_jobs,
    service_one,
    fake_uuid,
    user,
    key_type,
    notification_status,
    expected_status,
):

    mocker.patch('app.user_api_client.get_user', return_value=user(fake_uuid))

    _mock_get_notification = mock_get_notification(
        mocker,
        fake_uuid,
        notification_status=notification_status,
        key_type=key_type,
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


@pytest.mark.parametrize('extra_args, expected_back_link', [
    (
        {},
        partial(url_for, 'main.view_notifications', message_type='sms', status='sending,delivered,failed'),
    ),
    (
        {'from_job': 'job_id'},
        partial(url_for, 'main.view_job', job_id='job_id'),
    ),
    (
        {'help': '0'},
        None,
    ),
    (
        {'help': '1'},
        None,
    ),
    (
        {'help': '2'},
        None,
    ),
])
def test_notification_status_shows_expected_back_link(
    client_request,
    mocker,
    mock_get_notification,
    fake_uuid,
    extra_args,
    expected_back_link,
):
    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        **extra_args
    )
    back_link = page.select_one('.govuk-back-link')

    if expected_back_link:
        assert back_link['href'] == expected_back_link(service_id=SERVICE_ONE_ID)
    else:
        assert back_link is None


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
        "‘sample template’ was sent by Test User on 1 January at 1:01am"
    )
    assert len(page.select('main p:nth-of-type(1) a')) == 0


@freeze_time("2016-01-01 01:01")
def test_notification_page_shows_page_for_letter_notification(
    client_request,
    mocker,
    fake_uuid,
):

    count_of_pages = 3

    notification = mock_get_notification(
        mocker,
        fake_uuid,
        notification_status='created',
        template_type='letter',
        postage='second')
    notification.created_at = datetime.utcnow()

    mock_page_count = mocker.patch(
        'app.main.views.notifications.get_page_count_for_letter',
        return_value=count_of_pages
    )

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert normalize_spaces(page.select('main p:nth-of-type(1)')[0].text) == (
        "‘sample template’ was sent by Test User on 1 January at 1:01am"
    )
    assert normalize_spaces(page.select('main p:nth-of-type(2)')[0].text) == (
        'Printing starts today at 5:30pm'
    )
    assert normalize_spaces(page.select('main p:nth-of-type(3)')[0].text) == (
        'Estimated delivery date: 6 January'
    )
    assert len(page.select('.letter-postage')) == 1
    assert normalize_spaces(page.select_one('.letter-postage').text) == (
        'Postage: second class'
    )
    assert page.select_one('.letter-postage')['class'] == [
        'letter-postage', 'letter-postage-second'
    ]
    assert page.select('p.notification-status') == []

    letter_images = page.select('main img')

    assert len(letter_images) == count_of_pages

    for index in range(1, count_of_pages + 1):
        assert page.select('img')[index]['src'].endswith(
            '.png?page={}'.format(index)
        )

    assert len(mock_page_count.call_args_list) == 1
    assert mock_page_count.call_args_list[0][0][0]['name'] == 'sample template'
    assert mock_page_count.call_args_list[0][1]['values'] == {'name': 'Jo'}


@freeze_time("2016-01-01 01:01")
@pytest.mark.parametrize('is_precompiled_letter, expected_p1, expected_p2, expected_postage', (
    (
        True,
        'Provided as PDF on 1 January at 1:01am',
        'This letter passed our checks, but we will not print it because you used a test key.',
        'Postage: second class'
    ),
    (
        False,
        '‘sample template’ was sent on 1 January at 1:01am',
        'We will not print this letter because you used a test key.',
        'Postage: second class',
    ),
))
def test_notification_page_shows_page_for_letter_sent_with_test_key(
    client_request,
    mocker,
    fake_uuid,
    is_precompiled_letter,
    expected_p1,
    expected_p2,
    expected_postage,
):

    if is_precompiled_letter:
        mocker.patch(
            'app.main.views.notifications.view_letter_notification_as_preview',
            return_value=(b'foo', {
                'message': '',
                'invalid_pages': '[]',
                'page_count': '1'
            })
        )
    else:
        mocker.patch(
            'app.main.views.notifications.view_letter_notification_as_preview',
            return_value=b'foo'
        )

    mocker.patch(
        'app.main.views.notifications.pdf_page_count',
        return_value=1
    )

    mocker.patch(
        'app.main.views.notifications.get_page_count_for_letter',
        return_value=1,
    )

    notification = mock_get_notification(
        mocker,
        fake_uuid,
        notification_status='created',
        template_type='letter',
        is_precompiled_letter=is_precompiled_letter,
        postage='second',
        key_type='test',
        sent_one_off=False,
    )
    notification.created_at = datetime.utcnow()

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert normalize_spaces(page.select('main p:nth-of-type(1)')[0].text) == (
        expected_p1
    )
    assert normalize_spaces(page.select('main p:nth-of-type(2)')[0].text) == (
        expected_p2
    )
    assert normalize_spaces(
        page.select_one('.letter-postage').text
    ) == expected_postage
    assert page.select('p.notification-status') == []


@pytest.mark.parametrize('notification_status, expected_message', (
    (
        'permanent-failure',
        'Cancelled 1 January at 1:02am',
    ),
    (
        'cancelled',
        'Cancelled 1 January at 1:02am',
    ),
    (
        'validation-failed',
        'Validation failed.',
    ),
    (
        'technical-failure',
        'Technical failure – Notify will resend once the team have fixed the problem',
    ),
))
@freeze_time("2016-01-01 01:01")
def test_notification_page_shows_cancelled_or_failed_letter(
    client_request,
    mocker,
    fake_uuid,
    notification_status,
    expected_message,
):
    mock_get_notification(
        mocker,
        fake_uuid,
        template_type='letter',
        notification_status=notification_status,
    )
    mocker.patch(
        'app.main.views.notifications.get_page_count_for_letter',
        return_value=1,
    )

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert normalize_spaces(page.select('main p')[0].text) == (
        "‘sample template’ was sent by Test User on 1 January at 1:01am"
    )
    assert normalize_spaces(page.select('main p')[1].text) == (
        expected_message
    )
    assert not page.select('p.notification-status')

    assert page.select_one('main img')['src'].endswith('.png?page=1')


@pytest.mark.parametrize('notification_type', ['email', 'sms'])
@freeze_time('2016-01-01 15:00')
def test_notification_page_does_not_show_cancel_link_for_sms_or_email_notifications(
    client_request,
    mocker,
    fake_uuid,
    notification_type,
):
    mock_get_notification(
        mocker,
        fake_uuid,
        template_type=notification_type,
        notification_status='created',
    )

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert 'Cancel sending this letter' not in normalize_spaces(page.text)


@freeze_time('2016-01-01 15:00')
def test_notification_page_shows_cancel_link_for_letter_which_can_be_cancelled(
    client_request,
    mocker,
    fake_uuid,
):
    mock_get_notification(
        mocker,
        fake_uuid,
        template_type='letter',
        notification_status='created',
    )
    mocker.patch(
        'app.main.views.notifications.get_page_count_for_letter',
        return_value=1
    )

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert 'Cancel sending this letter' in normalize_spaces(page.text)


@freeze_time('2016-01-01 15:00')
def test_notification_page_does_not_show_cancel_link_for_letter_which_cannot_be_cancelled(
    client_request,
    mocker,
    fake_uuid,
):
    mock_get_notification(
        mocker,
        fake_uuid,
        template_type='letter',
        notification_status='delivered',
    )
    mocker.patch(
        'app.main.views.notifications.get_page_count_for_letter',
        return_value=1
    )

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert 'Cancel sending this letter' not in normalize_spaces(page.text)


@freeze_time("2016-01-01 18:00")
def test_notification_page_shows_page_for_first_class_letter_notification(
    client_request,
    mocker,
    fake_uuid,
):
    mock_get_notification(
        mocker,
        fake_uuid,
        notification_status='pending-virus-check',
        template_type='letter',
        postage='first')
    mocker.patch('app.main.views.notifications.get_page_count_for_letter', return_value=3)

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert normalize_spaces(page.select('main p:nth-of-type(2)')[0].text) == 'Printing starts tomorrow at 5:30pm'
    assert normalize_spaces(page.select('main p:nth-of-type(3)')[0].text) == 'Estimated delivery date: 5 January'
    assert normalize_spaces(page.select_one('.letter-postage').text) == (
        'Postage: first class'
    )
    assert page.select_one('.letter-postage')['class'] == [
        'letter-postage', 'letter-postage-first'
    ]


@pytest.mark.parametrize('filetype', [
    'pdf', 'png'
])
def test_should_show_image_of_letter_notification(
    logged_in_client,
    fake_uuid,
    mocker,
    filetype,
):

    mock_get_notification(mocker, fake_uuid, template_type='letter')

    mocker.patch(
        'app.main.views.notifications.notification_api_client.get_notification_letter_preview',
        return_value={
            'content': base64.b64encode(b'foo').decode('utf-8')
        }
    )

    response = logged_in_client.get(url_for(
        'main.view_letter_notification_as_preview',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        filetype=filetype
    ))

    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'foo'


def test_should_show_image_of_letter_notification_that_failed_validation(
    logged_in_client,
    fake_uuid,
    mocker
):

    mock_get_notification(mocker, fake_uuid, template_type='letter', notification_status='validation-failed')

    metadata = {
        'message': 'content-outside-printable-area',
        'invalid_pages': '[1]',
        'page_count': '1'
    }
    mocker.patch(
        'app.main.views.notifications.notification_api_client.get_notification_letter_preview',
        return_value={
            'content': base64.b64encode(b'foo').decode('utf-8'),
            'metadata': metadata
        }
    )

    response = logged_in_client.get(url_for(
        'main.view_letter_notification_as_preview',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        filetype='png',
        with_metadata=True
    ))

    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'foo', metadata


def test_should_show_preview_error_image_letter_notification_on_preview_error(
    logged_in_client,
    fake_uuid,
    mocker,
):

    mock_get_notification(mocker, fake_uuid, template_type='letter')

    mocker.patch(
        'app.main.views.notifications.notification_api_client.get_notification_letter_preview',
        side_effect=APIError
    )

    mocker.patch("builtins.open", mock_open(read_data="preview error image"))

    response = logged_in_client.get(url_for(
        'main.view_letter_notification_as_preview',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        filetype='png'
    ))

    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'preview error image'


def test_notifification_page_shows_error_message_if_precompiled_letter_cannot_be_opened(
    client_request,
    mocker,
    fake_uuid,
):
    mock_get_notification(
        mocker,
        fake_uuid,
        notification_status='validation-failed',
        template_type='letter',
        is_precompiled_letter=True,
    )
    mocker.patch(
        'app.main.views.notifications.view_letter_notification_as_preview',
        side_effect=PdfReadError()
    )
    mocker.patch(
        'app.main.views.notifications.pdf_page_count',
        side_effect=PdfReadError()
    )
    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    error_message = page.find('p', class_='notification-status-cancelled').text
    assert normalize_spaces(error_message) == "Validation failed – Notify cannot read this PDF file"


def test_should_404_for_unknown_extension(
    client_request,
    fake_uuid,
):
    client_request.get(
        'main.view_letter_notification_as_preview',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        filetype='docx',
        _expected_status=404,
    )


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
    mocker.patch(
        'app.main.views.notifications.get_page_count_for_letter',
        return_value=1
    )

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    last_paragraph = page.select('main p')[-1]
    conversation_link = url_for(
        '.conversation',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        _anchor='n{}'.format(fake_uuid),
    )

    if link_expected:
        assert normalize_spaces(last_paragraph.text) == (
            'See all text messages sent to this phone number'
        )
        assert last_paragraph.select_one('a')['href'] == conversation_link
    else:
        assert conversation_link not in str(page.select_one('main'))


@pytest.mark.parametrize('template_type, expected_link', [
    ('email', lambda notification_id: None),
    ('sms', lambda notification_id: None),
    ('letter', partial(
        url_for,
        'main.view_letter_notification_as_preview',
        service_id=SERVICE_ONE_ID,
        filetype='pdf'
    )),
])
def test_notification_page_has_link_to_download_letter(
    client_request,
    mocker,
    fake_uuid,
    service_one,
    template_type,
    expected_link,
):

    mock_get_notification(mocker, fake_uuid, template_type=template_type)
    mocker.patch(
        'app.main.views.notifications.get_page_count_for_letter',
        return_value=1
    )

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    try:
        download_link = page.select_one('a[download]')['href']
    except TypeError:
        download_link = None

    assert download_link == expected_link(notification_id=fake_uuid)


@pytest.mark.parametrize('is_precompiled_letter, has_template_link', [
    (True, False),
    (False, True),
])
def test_notification_page_has_expected_template_link_for_letter(
    client_request,
    mocker,
    fake_uuid,
    service_one,
    is_precompiled_letter,
    has_template_link
):

    if is_precompiled_letter:
        mocker.patch(
            'app.main.views.notifications.view_letter_notification_as_preview',
            side_effect=[(b'foo', {"message": "", "invalid_pages": "[]", "page_count": "1"}), b'foo']
        )
    else:
        mocker.patch(
            'app.main.views.notifications.view_letter_notification_as_preview',
            return_value=b'foo'
        )

    mocker.patch(
        'app.main.views.notifications.pdf_page_count',
        return_value=1
    )

    mock_get_notification(
        mocker, fake_uuid, template_type='letter', is_precompiled_letter=is_precompiled_letter)

    mocker.patch(
        'app.main.views.notifications.get_page_count_for_letter',
        return_value=1
    )

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    link = page.select_one('main > p:nth-of-type(1) > a')

    if has_template_link:
        assert link
    else:
        assert link is None


def test_should_show_image_of_precompiled_letter_notification(
    logged_in_client,
    fake_uuid,
    mocker,
):

    mock_get_notification(mocker, fake_uuid, template_type='letter', is_precompiled_letter=True)

    mock_pdf_page_count = mocker.patch(
        'app.main.views.notifications.pdf_page_count',
        return_value=1
    )

    mocker.patch(
        'app.main.views.notifications.notification_api_client.get_notification_letter_preview',
        return_value={
            'content': base64.b64encode(b'foo').decode('utf-8')
        }
    )

    response = logged_in_client.get(url_for(
        'main.view_letter_notification_as_preview',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        filetype="png"
    ))

    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'foo'
    assert mock_pdf_page_count.called_once()


@freeze_time('2016-01-01 15:00')
def test_show_cancel_letter_confirmation(
    client_request,
    mocker,
    fake_uuid,
):
    mock_get_notification(
        mocker,
        fake_uuid,
        template_type='letter',
        notification_status='created',
    )
    mocker.patch(
        'app.main.views.notifications.get_page_count_for_letter',
        return_value=1
    )

    page = client_request.get(
        'main.cancel_letter',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    flash_message = normalize_spaces(page.find('div', class_='banner-dangerous').text)

    assert 'Are you sure you want to cancel sending this letter?' in flash_message


@freeze_time('2016-01-01 15:00')
def test_cancelling_a_letter_calls_the_api(
    client_request,
    mocker,
    fake_uuid,
):
    mock_get_notification(
        mocker,
        fake_uuid,
        template_type='letter',
        notification_status='created',
    )
    mocker.patch(
        'app.main.views.notifications.get_page_count_for_letter',
        return_value=1
    )
    cancel_endpoint = mocker.patch(
        'app.main.views.notifications.notification_api_client.update_notification_to_cancelled'
    )

    client_request.post(
        'main.cancel_letter',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        _follow_redirects=True,
        _expected_redirect=None,
    )

    assert cancel_endpoint.called
