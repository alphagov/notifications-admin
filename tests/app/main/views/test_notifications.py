import base64
from functools import partial
from unittest.mock import mock_open

import pytest
from flask import url_for
from freezegun import freeze_time
from notifications_python_client.errors import APIError
from PyPDF2.utils import PdfReadError

from tests.conftest import (
    SERVICE_ONE_ID,
    create_active_caseworking_user,
    create_active_user_with_permissions,
    create_notification,
    normalize_spaces,
)


@pytest.mark.parametrize('key_type, notification_status, expected_status', [
    (None, 'created', 'Sending'),
    (None, 'sending', 'Sending'),
    (None, 'delivered', 'Delivered'),
    (None, 'failed', 'Failed'),
    (None, 'temporary-failure', 'Phone not accepting messages right now'),
    (None, 'permanent-failure', 'Not delivered'),
    (None, 'technical-failure', 'Technical failure'),
    ('team', 'delivered', 'Delivered'),
    ('live', 'delivered', 'Delivered'),
    ('test', 'sending', 'Sending (test)'),
    ('test', 'delivered', 'Delivered (test)'),
    ('test', 'permanent-failure', 'Not delivered (test)'),
])
@pytest.mark.parametrize('user', [
    create_active_user_with_permissions(),
    create_active_caseworking_user(),
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

    mocker.patch('app.user_api_client.get_user', return_value=user)

    notification = create_notification(notification_status=notification_status, key_type=key_type)
    _mock_get_notification = mocker.patch('app.notification_api_client.get_notification', return_value=notification)

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


@pytest.mark.parametrize('notification_type, notification_status, expected_class', [
    ('sms', 'failed', 'error'),
    ('email', 'failed', 'error'),
    ('sms', 'sent', 'sent-international'),
    ('email', 'sent', None),
    ('sms', 'created', 'default'),
    ('email', 'created', 'default'),
])
@freeze_time("2016-01-01 11:09:00.061258")
def test_notification_status_page_formats_email_and_sms_status_correctly(
    client_request,
    mocker,
    mock_has_no_jobs,
    service_one,
    fake_uuid,
    active_user_with_permissions,
    notification_type,
    notification_status,
    expected_class,
):
    mocker.patch('app.user_api_client.get_user', return_value=active_user_with_permissions)
    notification = create_notification(notification_status=notification_status, template_type=notification_type)
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)

    page = client_request.get(
        'main.view_notification',
        service_id=service_one['id'],
        notification_id=fake_uuid
    )
    assert page.select_one(f'.ajax-block-container p.notification-status.{expected_class}')


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

    _mock_get_notification = mocker.patch(
        'app.notification_api_client.get_notification',
        return_value=create_notification(redact_personalisation=template_redaction_setting)
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
        {'from_uploaded_letters': '2020-02-02'},
        partial(url_for, 'main.uploaded_letters', letter_print_day='2020-02-02'),
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


@pytest.mark.parametrize('time_of_viewing_page, expected_message', (
    ('2012-01-01 01:01', (
        "‘sample template’ was sent by Test User today at 1:01am"
    )),
    ('2012-01-02 01:01', (
        "‘sample template’ was sent by Test User yesterday at 1:01am"
    )),
    ('2012-01-03 01:01', (
        "‘sample template’ was sent by Test User on 1 January at 1:01am"
    )),
    ('2013-01-03 01:01', (
        "‘sample template’ was sent by Test User on 1 January 2012 at 1:01am"
    )),
))
def test_notification_page_doesnt_link_to_template_in_tour(
    mocker,
    client_request,
    fake_uuid,
    mock_get_notification,
    time_of_viewing_page,
    expected_message,
):

    with freeze_time('2012-01-01 01:01'):
        notification = create_notification()
        mocker.patch('app.notification_api_client.get_notification', return_value=notification)

    with freeze_time(time_of_viewing_page):
        page = client_request.get(
            'main.view_notification',
            service_id=SERVICE_ONE_ID,
            notification_id=fake_uuid,
            help=3,
        )

    assert normalize_spaces(page.select('main p:nth-of-type(1)')[0].text) == (
        expected_message
    )
    assert len(page.select('main p:nth-of-type(1) a')) == 0


@freeze_time("2016-01-01 01:01")
def test_notification_page_shows_page_for_letter_notification(
    client_request,
    mocker,
    fake_uuid,
):

    count_of_pages = 3

    notification = create_notification(notification_status='created', template_type='letter', postage='second')
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)

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
        "‘sample template’ was sent by Test User today at 1:01am"
    )
    assert normalize_spaces(page.select('main p:nth-of-type(2)')[0].text) == (
        'Printing starts today at 5:30pm'
    )
    assert normalize_spaces(page.select('main p:nth-of-type(3)')[0].text) == (
        'Estimated delivery date: Wednesday 6 January'
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
    for index in range(count_of_pages):
        assert page.select('img')[index]['src'].endswith(
            '.png?page={}'.format(index + 1)
        )

    assert len(mock_page_count.call_args_list) == 1
    assert mock_page_count.call_args_list[0][0][0]['name'] == 'sample template'
    assert mock_page_count.call_args_list[0][1]['values'] == {'name': 'Jo'}


@freeze_time("2020-01-01 00:00")
def test_notification_page_shows_uploaded_letter(
    client_request,
    mocker,
    fake_uuid,
):
    mocker.patch(
        'app.main.views.notifications.get_letter_file_data',
        return_value=(b'foo', {
            'message': '',
            'invalid_pages': '[]',
            'page_count': '1'
        })
    )
    mocker.patch(
        'app.main.views.notifications.pdf_page_count',
        return_value=1
    )
    mocker.patch(
        'app.main.views.notifications.get_page_count_for_letter',
        return_value=1,
    )

    notification = create_notification(
        notification_status='created',
        template_type='letter',
        is_precompiled_letter=True,
        sent_one_off=True,
    )
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert normalize_spaces(page.select('main p:nth-of-type(1)')[0].text) == (
        'Uploaded by Test User yesterday at midnight'
    )
    assert normalize_spaces(page.select('main p:nth-of-type(2)')[0].text) == (
        'Printing starts today at 5:30pm'
    )


@freeze_time("2016-01-01 01:01")
@pytest.mark.parametrize('is_precompiled_letter, expected_p1, expected_p2, expected_postage', (
    (
        True,
        'Provided as PDF today at 1:01am',
        'This letter passed our checks, but we will not print it because you used a test key.',
        'Postage: second class'
    ),
    (
        False,
        '‘sample template’ was sent today at 1:01am',
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
            'app.main.views.notifications.get_letter_file_data',
            return_value=(b'foo', {
                'message': '',
                'invalid_pages': '[]',
                'page_count': '1'
            })
        )

    mocker.patch(
        'app.main.views.notifications.pdf_page_count',
        return_value=1
    )

    mocker.patch(
        'app.main.views.notifications.get_page_count_for_letter',
        return_value=1,
    )

    notification = create_notification(
        notification_status='created',
        template_type='letter',
        is_precompiled_letter=is_precompiled_letter,
        postage='second',
        key_type='test',
        sent_one_off=False,
    )
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)

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


def test_notification_page_shows_validation_failed_precompiled_letter(
    client_request,
    mocker,
    fake_uuid,
):
    notification = create_notification(template_type='letter',
                                       notification_status='validation-failed',
                                       is_precompiled_letter=True
                                       )
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)
    metadata = {"page_count": "1", "status": "validation-failed",
                "invalid_pages": "[1]",
                "message": "content-outside-printable-area"}
    mocker.patch('app.main.views.notifications.get_letter_file_data',
                 return_value=("some letter content", metadata))
    mocker.patch(
        'app.main.views.notifications.get_page_count_for_letter',
        return_value=1,
    )

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    error_message = page.find('p', class_='notification-status-cancelled').text
    assert normalize_spaces(error_message) == (
        'Validation failed because content is outside the printable area on page 1.'
        'Files must meet our letter specification.'
    )

    assert not page.select('p.notification-status')

    assert page.select_one('main img')['src'].endswith('.png?page=1')
    assert not page.select('.letter-postage')


@pytest.mark.parametrize('notification_status, expected_message', (
    (
        'permanent-failure',
        'Permanent failure – The postal provider is unable to print the letter. Your letter has not been sent.',
    ),
    (
        'cancelled',
        'Cancelled 1 January at 1:02am',
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
    notification = create_notification(template_type='letter', notification_status=notification_status)
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)
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
        "‘sample template’ was sent by Test User today at 1:01am"
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
    notification = create_notification(template_type=notification_type, notification_status='created')
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)

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
    notification = create_notification(template_type='letter', notification_status='created')
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)

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
    notification = create_notification(template_type='letter')
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)

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


@pytest.mark.parametrize('postage, expected_postage_text, expected_class_value, expected_delivery', (
    (
        'first',
        'Postage: first class',
        'letter-postage-first',
        'Estimated delivery date: Tuesday 5 January',
    ),
    (
        'europe',
        'Postage: international',
        'letter-postage-international',
        'Estimated delivery date: Friday 8 January',
    ),
    (
        'rest-of-world',
        'Postage: international',
        'letter-postage-international',
        'Estimated delivery date: Monday 11 January',
    ),
))
@freeze_time("2016-01-01 18:00")
def test_notification_page_shows_page_for_other_postage_classes(
    client_request,
    mocker,
    fake_uuid,
    postage,
    expected_postage_text,
    expected_class_value,
    expected_delivery,
):
    notification = create_notification(
        notification_status='pending-virus-check',
        template_type='letter',
        postage=postage,
    )
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)
    mocker.patch('app.main.views.notifications.get_page_count_for_letter', return_value=3)

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert normalize_spaces(page.select('main p:nth-of-type(2)')[0].text) == 'Printing starts tomorrow at 5:30pm'
    assert normalize_spaces(page.select('main p:nth-of-type(3)')[0].text) == (
        expected_delivery
    )
    assert normalize_spaces(page.select_one('.letter-postage').text) == (
        expected_postage_text
    )
    assert page.select_one('.letter-postage')['class'] == [
        'letter-postage', expected_class_value
    ]


@pytest.mark.parametrize('filetype', [
    'pdf', 'png'
])
@pytest.mark.parametrize('user', [
    create_active_user_with_permissions(),
    create_active_caseworking_user(),
])
def test_should_show_image_of_letter_notification(
    logged_in_client,
    fake_uuid,
    mocker,
    filetype,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user)

    notification = create_notification(template_type='letter')
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)

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
    notification = create_notification(template_type='letter', notification_status='validation-failed')
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)

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
    notification = create_notification(template_type='letter')
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)

    mocker.patch(
        'app.main.views.notifications.notification_api_client.get_notification_letter_preview',
        side_effect=APIError
    )

    mocker.patch("builtins.open", mock_open(read_data=b"preview error image"))

    response = logged_in_client.get(url_for(
        'main.view_letter_notification_as_preview',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        filetype='png'
    ))

    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'preview error image'


def test_notification_page_shows_error_message_if_precompiled_letter_cannot_be_opened(
    client_request,
    mocker,
    fake_uuid,
):
    notification = create_notification(
        notification_status='validation-failed',
        template_type='letter',
        is_precompiled_letter=True)
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)
    mocker.patch(
        'app.main.views.notifications.get_letter_file_data',
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
    assert normalize_spaces(error_message) == \
        "Validation failed – There’s a problem with your letter. Notify cannot read this PDF."


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
    notification = create_notification(template_type=template_type)
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)
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
    notification = create_notification(template_type=template_type)
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)
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
            'app.main.views.notifications.get_letter_file_data',
            side_effect=[(b'foo', {"message": "", "invalid_pages": "[]", "page_count": "1"}), b'foo']
        )

    mocker.patch(
        'app.main.views.notifications.pdf_page_count',
        return_value=1
    )

    notification = create_notification(template_type='letter', is_precompiled_letter=is_precompiled_letter)
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)
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
    notification = create_notification(template_type='letter', is_precompiled_letter=True)
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)
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
    notification = create_notification(template_type='letter', notification_status='created')
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)
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
    notification = create_notification(template_type='letter', notification_status='created')
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)
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


@pytest.mark.parametrize('notification_type', ['sms', 'email'])
def test_should_show_reply_to_from_notification(
    mocker,
    fake_uuid,
    notification_type,
    client_request,
):
    notification = create_notification(reply_to_text='reply to info', template_type=notification_type)
    mocker.patch('app.notification_api_client.get_notification', return_value=notification)

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert 'reply to info' in page.text
