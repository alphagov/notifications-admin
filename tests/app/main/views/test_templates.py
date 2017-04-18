from itertools import repeat
from datetime import datetime
from unittest.mock import Mock, patch, ANY

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError
from tests.conftest import service_one as create_sample_service
from tests.conftest import mock_get_service_email_template, mock_get_service_letter_template
from tests import validate_route_permission, template_json, single_notification_json
from tests.app.test_utils import normalize_spaces

from app.main.views.templates import get_last_use_message, get_human_readable_delta


def test_should_show_page_for_one_template(
    logged_in_client,
    mock_get_service_template,
    service_one,
    fake_uuid,
):
    template_id = fake_uuid
    response = logged_in_client.get(url_for(
        '.edit_service_template',
        service_id=service_one['id'],
        template_id=template_id))

    assert response.status_code == 200
    assert "Two week reminder" in response.get_data(as_text=True)
    assert "Template &lt;em&gt;content&lt;/em&gt; with &amp; entity" in response.get_data(as_text=True)
    assert "Use priority queue?" not in response.get_data(as_text=True)
    mock_get_service_template.assert_called_with(service_one['id'], template_id)


@pytest.mark.parametrize('permissions, links_to_be_shown', [
    (
        ['view_activity'],
        []
    ),
    (
        ['manage_templates'],
        ['.edit_service_template']
    ),
    (
        ['send_texts', 'send_emails', 'send_letters'],
        ['.send_messages', '.send_test']
    ),
    (
        ['send_texts', 'send_emails', 'send_letters', 'manage_templates'],
        ['.send_messages', '.send_test', '.edit_service_template']
    ),
])
def test_should_be_able_to_view_a_template_with_links(
    client,
    mock_get_service_template,
    active_user_with_permissions,
    mocker,
    service_one,
    fake_uuid,
    permissions,
    links_to_be_shown,
):
    active_user_with_permissions._permissions[service_one['id']] = permissions
    client.login(active_user_with_permissions, mocker, service_one)

    response = client.get(url_for(
        '.view_template',
        service_id=service_one['id'],
        template_id=fake_uuid
    ))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    links_in_page = page.select('.pill-separate-item')

    assert len(links_in_page) == len(links_to_be_shown)

    for index, link_to_be_shown in enumerate(links_to_be_shown):
        assert links_in_page[index]['href'] == url_for(
            link_to_be_shown,
            service_id=service_one['id'],
            template_id=fake_uuid,
        )


def test_should_show_template_id_on_template_page(
    logged_in_client,
    mock_get_service_template,
    service_one,
    fake_uuid,
):

    response = logged_in_client.get(url_for(
        '.view_template',
        service_id=service_one['id'],
        template_id=fake_uuid))

    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.select('.api-key-key')[0].text == fake_uuid


def test_should_show_sms_template_with_downgraded_unicode_characters(
    logged_in_client,
    mocker,
    service_one,
    fake_uuid,
):
    msg = 'here:\tare some “fancy quotes” and zero\u200Bwidth\u200Bspaces'
    rendered_msg = 'here: are some "fancy quotes" and zerowidthspaces'

    mocker.patch(
        'app.service_api_client.get_service_template',
        return_value={'data': template_json(service_one['id'], fake_uuid, type_='sms', content=msg)}
    )

    template_id = fake_uuid
    response = logged_in_client.get(url_for(
        '.view_template',
        service_id=service_one['id'],
        template_id=template_id))

    assert response.status_code == 200
    assert rendered_msg in response.get_data(as_text=True)


def test_should_show_page_template_with_priority_select_if_platform_admin(
    logged_in_platform_admin_client,
    platform_admin_user,
    mocker,
    mock_get_service_template,
    fake_uuid,
):
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[platform_admin_user])
    template_id = fake_uuid
    response = logged_in_platform_admin_client.get(url_for(
        '.edit_service_template',
        service_id='1234',
        template_id=template_id))

    assert response.status_code == 200
    assert "Two week reminder" in response.get_data(as_text=True)
    assert "Template &lt;em&gt;content&lt;/em&gt; with &amp; entity" in response.get_data(as_text=True)
    assert "Use priority queue?" in response.get_data(as_text=True)
    mock_get_service_template.assert_called_with('1234', template_id)


@pytest.mark.parametrize('view_suffix, expected_content_type', [
    ('as_pdf', 'application/pdf'),
    ('as_png', 'image/png'),
])
@pytest.mark.parametrize('view, extra_view_args', [
    ('.view_letter_template', {}),
    ('.view_template_version', {'version': 1}),
])
@patch('app.main.views.templates.LetterPreviewTemplate.jinja_template.render', return_value='foo')
def test_should_show_preview_letter_templates(
    mock_letter_preview,
    view,
    extra_view_args,
    view_suffix,
    expected_content_type,
    logged_in_client,
    mock_get_service_email_template,
    mock_get_user_by_email,
    service_one,
    fake_uuid
):
    service_id, template_id = service_one['id'], fake_uuid
    response = logged_in_client.get(url_for(
        '{}_{}'.format(view, view_suffix),
        service_id=service_id,
        template_id=template_id,
        **extra_view_args
    ))

    assert response.status_code == 200
    assert response.content_type == expected_content_type
    mock_get_service_email_template.assert_called_with(service_id, template_id, **extra_view_args)
    assert mock_letter_preview.call_args[0][0]['subject'] == (
        "Your <span class='placeholder'>((thing))</span> is due soon"
    )
    assert mock_letter_preview.call_args[0][0]['message'] == (
        "<p>Your vehicle tax expires on <span class='placeholder'>((date))</span></p>"
    )


def test_should_redirect_when_saving_a_template(
    logged_in_client,
    active_user_with_permissions,
    mocker,
    mock_get_service_template,
    mock_update_service_template,
    fake_uuid,
):
    service = create_sample_service(active_user_with_permissions)
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])
    template_id = fake_uuid
    name = "new name"
    content = "template <em>content</em> with & entity"
    data = {
        'id': template_id,
        'name': name,
        'template_content': content,
        'template_type': 'sms',
        'service': service['id'],
        'process_type': 'normal'
    }
    response = logged_in_client.post(url_for(
        '.edit_service_template',
        service_id=service['id'],
        template_id=template_id), data=data)

    assert response.status_code == 302
    assert response.location == url_for(
        '.view_template', service_id=service['id'], template_id=template_id, _external=True)
    mock_update_service_template.assert_called_with(
        template_id, name, 'sms', content, service['id'], None, 'normal')


def test_should_edit_content_when_process_type_is_priority_not_platform_admin(
    logged_in_client,
    active_user_with_permissions,
    mocker,
    mock_get_service_template_with_priority,
    mock_update_service_template,
    fake_uuid,
):
    service = create_sample_service(active_user_with_permissions)
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])
    template_id = fake_uuid
    data = {
        'id': template_id,
        'name': "new name",
        'template_content': "new template <em>content</em> with & entity",
        'template_type': 'sms',
        'service': service['id'],
        'process_type': 'priority'
    }
    response = logged_in_client.post(url_for(
        '.edit_service_template',
        service_id=service['id'],
        template_id=template_id), data=data)
    assert response.status_code == 302
    assert response.location == url_for(
        '.view_template', service_id=service['id'], template_id=template_id, _external=True)
    mock_update_service_template.assert_called_with(
        template_id,
        "new name",
        'sms',
        "new template <em>content</em> with & entity",
        service['id'],
        None,
        'priority'
    )


def test_should_403_when_edit_template_with_process_type_of_priority_for_non_platform_admin(
    client,
    active_user_with_permissions,
    mocker,
    mock_get_service_template,
    mock_update_service_template,
    fake_uuid,
):
    service = create_sample_service(active_user_with_permissions)
    client.login(active_user_with_permissions, mocker, service)
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])
    template_id = fake_uuid
    data = {
        'id': template_id,
        'name': "new name",
        'template_content': "template <em>content</em> with & entity",
        'template_type': 'sms',
        'service': service['id'],
        'process_type': 'priority'
    }
    response = client.post(url_for(
        '.edit_service_template',
        service_id=service['id'],
        template_id=template_id), data=data)
    assert response.status_code == 403
    mock_update_service_template.called == 0


def test_should_403_when_create_template_with_process_type_of_priority_for_non_platform_admin(
    client,
    active_user_with_permissions,
    mocker,
    mock_get_service_template,
    mock_update_service_template,
    fake_uuid,
):
    service = create_sample_service(active_user_with_permissions)
    client.login(active_user_with_permissions, mocker, service)
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])
    template_id = fake_uuid
    data = {
        'id': template_id,
        'name': "new name",
        'template_content': "template <em>content</em> with & entity",
        'template_type': 'sms',
        'service': service['id'],
        'process_type': 'priority'
    }
    response = client.post(url_for(
        '.add_service_template',
        service_id=service['id'],
        template_type='sms'), data=data)
    assert response.status_code == 403
    mock_update_service_template.called == 0


@pytest.mark.parametrize('template_mock, expected_paragraphs', [
    (
        mock_get_service_email_template,
        [
            'You removed ((date))',
            'You added ((name))',
            'When you send messages using this template you’ll need 3 columns of data:',
        ]
    ),
    (
        mock_get_service_letter_template,
        [
            'You removed ((date))',
            'You added ((name))',
            'When you send messages using this template you’ll need 9 columns of data:',
        ]
    ),
])
def test_should_show_interstitial_when_making_breaking_change(
    logged_in_client,
    api_user_active,
    mock_login,
    mock_update_service_template,
    mock_get_user,
    mock_get_service,
    mock_get_user_by_email,
    mock_has_permissions,
    fake_uuid,
    mocker,
    template_mock,
    expected_paragraphs,
):
    template_mock(
        mocker,
        subject="Your ((thing)) is due soon",
        content="Your vehicle tax expires on ((date))",
    )
    service_id = fake_uuid
    template_id = fake_uuid
    response = logged_in_client.post(
        url_for('.edit_service_template', service_id=service_id, template_id=template_id),
        data={
            'id': template_id,
            'name': "new name",
            'template_content': "hello lets talk about ((thing))",
            'template_type': 'email',
            'subject': 'reminder \'" <span> & ((name))',
            'service': service_id,
            'process_type': 'normal'
        }
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == "Confirm changes"
    assert page.find('a', {'class': 'page-footer-back-link'})['href'] == url_for(".edit_service_template",
                                                                                 service_id=service_id,
                                                                                 template_id=template_id)
    for index, p in enumerate(expected_paragraphs):
        assert normalize_spaces(page.select('main p')[index].text) == p

    for key, value in {
        'name': 'new name',
        'subject': 'reminder \'" <span> & ((name))',
        'template_content': 'hello lets talk about ((thing))',
        'confirm': 'true'
    }.items():
        assert page.find('input', {'name': key})['value'] == value

    # BeautifulSoup returns the value attribute as unencoded, let’s make
    # sure that it is properly encoded in the HTML
    assert str(page.find('input', {'name': 'subject'})) == (
        """<input name="subject" type="hidden" value="reminder '&quot; &lt;span&gt; &amp; ((name))"/>"""
    )


def test_should_not_create_too_big_template(
    logged_in_client,
    service_one,
    mock_get_service_template,
    mock_create_service_template_content_too_big,
    fake_uuid,
):
    template_type = 'sms'
    data = {
        'name': "new name",
        'template_content': "template content",
        'template_type': template_type,
        'service': service_one['id'],
        'process_type': 'normal'
    }
    resp = logged_in_client.post(url_for(
        '.add_service_template',
        service_id=service_one['id'],
        template_type=template_type
    ), data=data)

    assert resp.status_code == 200
    assert "Content has a character count greater than the limit of 459" in resp.get_data(as_text=True)


def test_should_not_update_too_big_template(
    logged_in_client,
    service_one,
    mock_get_service_template,
    mock_update_service_template_400_content_too_big,
    fake_uuid,
):
    template_id = fake_uuid
    data = {
        'id': fake_uuid,
        'name': "new name",
        'template_content': "template content",
        'service': service_one['id'],
        'template_type': 'sms',
        'process_type': 'normal'
    }
    resp = logged_in_client.post(url_for(
        '.edit_service_template',
        service_id=service_one['id'],
        template_id=template_id), data=data)

    assert resp.status_code == 200
    assert "Content has a character count greater than the limit of 459" in resp.get_data(as_text=True)


def test_should_redirect_when_saving_a_template_email(
    logged_in_client,
    api_user_active,
    mock_login,
    mock_get_service_email_template,
    mock_update_service_template,
    mock_get_user,
    mock_get_service,
    mock_get_user_by_email,
    mock_has_permissions,
    fake_uuid,
):
    service_id = fake_uuid
    template_id = fake_uuid
    name = "new name"
    content = "template <em>content</em> with & entity ((thing)) ((date))"
    subject = "subject & entity"
    data = {
        'id': template_id,
        'name': name,
        'template_content': content,
        'template_type': 'email',
        'service': service_id,
        'subject': subject,
        'process_type': 'normal'
    }
    response = logged_in_client.post(url_for(
        '.edit_service_template',
        service_id=service_id,
        template_id=template_id), data=data)
    assert response.status_code == 302
    assert response.location == url_for(
        '.view_template',
        service_id=service_id,
        template_id=template_id,
        _external=True)
    mock_update_service_template.assert_called_with(
        template_id, name, 'email', content, service_id, subject, 'normal')


def test_should_show_delete_template_page_with_time_block(
    logged_in_client,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_get_user,
    mock_get_user_by_email,
    mock_has_permissions,
    fake_uuid,
    mocker,
):
    with freeze_time('2012-01-01 12:00:00'):
        template = template_json('1234', '1234', "Test template", "sms", "Something very interesting")
        notification = single_notification_json('1234', template=template)

        mocker.patch('app.template_statistics_client.get_template_statistics_for_template',
                     return_value=notification)

    with freeze_time('2012-01-01 12:10:00'):
        service_id = fake_uuid
        template_id = fake_uuid
        response = logged_in_client.get(url_for(
            '.delete_service_template',
            service_id=service_id,
            template_id=template_id))
    content = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Test template was last used 10 minutes ago. Are you sure you want to delete it?' in content
    assert 'Are you sure' in content
    assert 'Two week reminder' in content
    assert 'Template &lt;em&gt;content&lt;/em&gt; with &amp; entity' in content
    mock_get_service_template.assert_called_with(service_id, template_id)


def test_should_show_delete_template_page_with_never_used_block(
    logged_in_client,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_get_user,
    mock_get_user_by_email,
    mock_has_permissions,
    fake_uuid,
    mocker,
):
    mocker.patch(
        'app.template_statistics_client.get_template_statistics_for_template',
        side_effect=HTTPError(response=Mock(status_code=404), message="Default message")
    )
    service_id = fake_uuid
    template_id = fake_uuid
    response = logged_in_client.get(url_for(
        '.delete_service_template',
        service_id=service_id,
        template_id=template_id))

    content = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Two week reminder has never been used. Are you sure you want to delete it?' in content
    assert 'Are you sure' in content
    assert 'Two week reminder' in content
    assert 'Template &lt;em&gt;content&lt;/em&gt; with &amp; entity' in content
    mock_get_service_template.assert_called_with(service_id, template_id)


def test_should_redirect_when_deleting_a_template(
    logged_in_client,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_delete_service_template,
    mock_get_user,
    mock_get_user_by_email,
    mock_has_permissions,
    fake_uuid,
):
    service_id = fake_uuid
    template_id = fake_uuid
    name = "new name"
    type_ = "sms"
    content = "template content"
    data = {
        'id': str(template_id),
        'name': name,
        'template_type': type_,
        'content': content,
        'service': service_id
    }
    response = logged_in_client.post(url_for(
        '.delete_service_template',
        service_id=service_id,
        template_id=template_id
    ), data=data)

    assert response.status_code == 302
    assert response.location == url_for(
        '.choose_template',
        service_id=service_id, _external=True)
    mock_get_service_template.assert_called_with(
        service_id, template_id)
    mock_delete_service_template.assert_called_with(
        service_id, template_id)


@freeze_time('2016-01-01T15:00')
def test_should_show_page_for_a_deleted_template(
    logged_in_client,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_deleted_template,
    mock_get_user,
    mock_get_user_by_email,
    mock_has_permissions,
    fake_uuid,
):
    service_id = fake_uuid
    template_id = fake_uuid
    response = logged_in_client.get(url_for(
        '.view_template',
        service_id=service_id,
        template_id=template_id
    ))

    assert response.status_code == 200

    content = response.get_data(as_text=True)
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert url_for("main.edit_service_template", service_id=fake_uuid, template_id=fake_uuid) not in content
    assert url_for("main.send_test", service_id=fake_uuid, template_id=fake_uuid) not in content
    assert page.select('p.hint')[0].text.strip() == 'This template was deleted today at 3:00pm.'

    mock_get_deleted_template.assert_called_with(service_id, template_id)


@pytest.mark.parametrize('route', [
    'main.add_service_template',
    'main.edit_service_template',
    'main.delete_service_template'
])
def test_route_permissions(
    route,
    mocker,
    app_,
    client,
    api_user_active,
    service_one,
    mock_get_service_template,
    mock_get_template_statistics_for_template,
    fake_uuid,
):
    validate_route_permission(
        mocker,
        app_,
        "GET",
        200,
        url_for(
            route,
            service_id=service_one['id'],
            template_type='sms',
            template_id=fake_uuid),
        ['manage_templates'],
        api_user_active,
        service_one)


def test_route_permissions_for_choose_template(
    mocker,
    app_,
    client,
    api_user_active,
    service_one,
    mock_get_service_templates,
):
    mocker.patch('app.job_api_client.get_job')
    validate_route_permission(
        mocker,
        app_,
        "GET",
        200,
        url_for(
            'main.choose_template',
            service_id=service_one['id'],
        ),
        ['view_activity'],
        api_user_active,
        service_one)


@pytest.mark.parametrize('route', [
    'main.add_service_template',
    'main.edit_service_template',
    'main.delete_service_template'
])
def test_route_invalid_permissions(
    route,
    mocker,
    app_,
    client,
    api_user_active,
    service_one,
    mock_get_service_template,
    mock_get_template_statistics_for_template,
    fake_uuid,
):
    validate_route_permission(
        mocker,
        app_,
        "GET",
        403,
        url_for(
            route,
            service_id=service_one['id'],
            template_type='sms',
            template_id=fake_uuid),
        ['view_activity'],
        api_user_active,
        service_one)


def test_get_last_use_message_returns_no_template_message():
    assert get_last_use_message('My Template', []) == 'My Template has never been used'


@freeze_time('2000-01-01T15:00')
def test_get_last_use_message_uses_most_recent_statistics():
    template_statistics = [
        {
            'updated_at': '2000-01-01T12:00:00.000000+00:00'
        },
        {
            'updated_at': '2000-01-01T09:00:00.000000+00:00'
        },
    ]
    assert get_last_use_message('My Template', template_statistics) == 'My Template was last used 3 hours ago'


@pytest.mark.parametrize('from_time, until_time, message', [
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 1, 12, 0, 59), 'under a minute'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 1, 12, 1), '1 minute'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 1, 12, 2, 35), '2 minutes'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 1, 12, 59), '59 minutes'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 1, 13, 0), '1 hour'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 1, 14, 0), '2 hours'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 2, 11, 59), '23 hours'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 2, 12, 0), '1 day'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 3, 14, 0), '2 days'),
])
def test_get_human_readable_delta(from_time, until_time, message):
    assert get_human_readable_delta(from_time, until_time) == message


def test_can_create_email_template_with_emoji(
    logged_in_client,
    service_one,
    mock_create_service_template
):
    data = {
        'name': "new name",
        'subject': "Food incoming!",
        'template_content': "here's a burrito 🌯",
        'template_type': 'email',
        'service': service_one['id'],
        'process_type': 'normal'
    }
    resp = logged_in_client.post(url_for(
        '.add_service_template',
        service_id=service_one['id'],
        template_type='email'
    ), data=data)

    assert resp.status_code == 302


def test_should_not_create_sms_template_with_emoji(
    logged_in_client,
    service_one,
    mock_create_service_template
):
    data = {
        'name': "new name",
        'template_content': "here are some noodles 🍜",
        'template_type': 'sms',
        'service': service_one['id'],
        'process_type': 'normal'
    }
    resp = logged_in_client.post(url_for(
        '.add_service_template',
        service_id=service_one['id'],
        template_type='sms'
    ), data=data)

    assert resp.status_code == 200
    assert "You can’t use 🍜 in text messages." in resp.get_data(as_text=True)


def test_should_not_update_sms_template_with_emoji(
    logged_in_client,
    service_one,
    mock_get_service_template,
    mock_update_service_template,
    fake_uuid,
):
    data = {
        'id': fake_uuid,
        'name': "new name",
        'template_content': "here's a burger 🍔",
        'service': service_one['id'],
        'template_type': 'sms',
        'process_type': 'normal'
    }
    resp = logged_in_client.post(url_for(
        '.edit_service_template',
        service_id=service_one['id'],
        template_id=fake_uuid), data=data)

    assert resp.status_code == 200
    assert "You can’t use 🍔 in text messages." in resp.get_data(as_text=True)


def test_should_create_sms_template_without_downgrading_unicode_characters(
    logged_in_client,
    service_one,
    mock_create_service_template
):
    msg = 'here:\tare some “fancy quotes” and non\u200Bbreaking\u200Bspaces'

    data = {
        'name': "new name",
        'template_content': msg,
        'template_type': 'sms',
        'service': service_one['id'],
        'process_type': 'normal'
    }
    resp = logged_in_client.post(url_for(
        '.add_service_template',
        service_id=service_one['id'],
        template_type='sms'
    ), data=data)

    mock_create_service_template.assert_called_with(
        ANY,  # name
        ANY,  # type
        msg,  # content
        ANY,  # service_id
        ANY,  # subject
        ANY  # process_type
    )
    assert resp.status_code == 302
