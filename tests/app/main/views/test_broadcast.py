import json
import uuid
from functools import partial

import pytest
from flask import url_for
from freezegun import freeze_time

from tests import broadcast_message_json, sample_uuid, user_json
from tests.conftest import SERVICE_ONE_ID, normalize_spaces

sample_uuid = sample_uuid()


@pytest.mark.parametrize('endpoint, extra_args, expected_get_status, expected_post_status', (
    (
        '.broadcast_dashboard', {},
        403, 405,
    ),
    (
        '.broadcast_dashboard_updates', {},
        403, 405,
    ),
    (
        '.broadcast',
        {'template_id': sample_uuid},
        403, 405,
    ),
    (
        '.preview_broadcast_areas', {'broadcast_message_id': sample_uuid},
        403, 405,
    ),
    (
        '.choose_broadcast_library', {'broadcast_message_id': sample_uuid},
        403, 405,
    ),
    (
        '.choose_broadcast_area', {'broadcast_message_id': sample_uuid, 'library_slug': 'countries'},
        403, 403,
    ),
    (
        '.remove_broadcast_area', {'broadcast_message_id': sample_uuid, 'area_slug': 'countries-E92000001'},
        403, 405,
    ),
    (
        '.preview_broadcast_message', {'broadcast_message_id': sample_uuid},
        403, 403,
    ),
    (
        '.view_broadcast_message', {'broadcast_message_id': sample_uuid},
        403, 403,
    ),
    (
        '.cancel_broadcast_message', {'broadcast_message_id': sample_uuid},
        403, 403,
    ),
))
def test_broadcast_pages_403_without_permission(
    client_request,
    endpoint,
    extra_args,
    expected_get_status,
    expected_post_status,
):
    client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_get_status,
        **extra_args
    )
    client_request.post(
        endpoint,
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_post_status,
        **extra_args
    )


@pytest.mark.parametrize('endpoint, extra_args, expected_get_status, expected_post_status', (
    (
        '.broadcast',
        {'template_id': sample_uuid},
        403, 405,
    ),
    (
        '.preview_broadcast_areas', {'broadcast_message_id': sample_uuid},
        403, 405,
    ),
    (
        '.choose_broadcast_library', {'broadcast_message_id': sample_uuid},
        403, 405,
    ),
    (
        '.choose_broadcast_area', {'broadcast_message_id': sample_uuid, 'library_slug': 'countries'},
        403, 403,
    ),
    (
        '.remove_broadcast_area', {'broadcast_message_id': sample_uuid, 'area_slug': 'england'},
        403, 405,
    ),
    (
        '.preview_broadcast_message', {'broadcast_message_id': sample_uuid},
        403, 403,
    ),
    (
        '.cancel_broadcast_message', {'broadcast_message_id': sample_uuid},
        403, 403,
    ),
))
def test_broadcast_pages_403_for_user_without_permission(
    mocker,
    client_request,
    service_one,
    active_user_view_permissions,
    endpoint,
    extra_args,
    expected_get_status,
    expected_post_status,
):
    service_one['permissions'] += ['broadcast']
    mocker.patch('app.user_api_client.get_user', return_value=active_user_view_permissions)
    client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_get_status,
        **extra_args
    )
    client_request.post(
        endpoint,
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_post_status,
        **extra_args
    )


def test_dashboard_redirects_to_broadcast_dashboard(
    client_request,
    service_one,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.service_dashboard',
        service_id=SERVICE_ONE_ID,
        _expected_redirect=url_for(
            '.broadcast_dashboard',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    ),


def test_empty_broadcast_dashboard(
    client_request,
    service_one,
    active_user_view_permissions,
    mock_get_no_broadcast_messages,
    mock_get_service_templates_when_no_templates_exist,
):
    service_one['permissions'] += ['broadcast']
    page = client_request.get(
        '.broadcast_dashboard',
        service_id=SERVICE_ONE_ID,
    )
    assert [
        normalize_spaces(row.text) for row in page.select('tbody tr .table-empty-message')
    ] == [
        'You do not have any live broadcasts at the moment',
        'You do not have any broadcasts waiting for approval',
        'You do not have any previous broadcasts',
    ]


@freeze_time('2020-02-20 02:20')
def test_broadcast_dashboard(
    client_request,
    service_one,
    mock_get_broadcast_messages,
    mock_get_service_templates,
):
    service_one['permissions'] += ['broadcast']
    page = client_request.get(
        '.broadcast_dashboard',
        service_id=SERVICE_ONE_ID,
    )

    assert normalize_spaces(page.select('main h2')[0].text) == (
        'Live broadcasts'
    )
    assert [
        normalize_spaces(row.text) for row in page.select('table')[0].select('tbody tr')
    ] == [
        'Example template To England and Scotland Live until tomorrow at 2:20am',
    ]

    assert normalize_spaces(page.select('main h2')[1].text) == (
        'Waiting for approval'
    )
    assert [
        normalize_spaces(row.text) for row in page.select('table')[1].select('tbody tr')
    ] == [
        'Example template To England and Scotland Prepared by Test User',
    ]

    assert normalize_spaces(page.select('main h2')[2].text) == (
        'Previous broadcasts'
    )
    assert [
        normalize_spaces(row.text) for row in page.select('table')[2].select('tbody tr')
    ] == [
        'Example template To England and Scotland Stopped 10 February at 2:20am',
        'Example template To England and Scotland Finished yesterday at 8:20pm',
    ]


@freeze_time('2020-02-20 02:20')
def test_broadcast_dashboard_json(
    logged_in_client,
    service_one,
    active_user_view_permissions,
    mock_get_broadcast_messages,
):
    service_one['permissions'] += ['broadcast']
    response = logged_in_client.get(url_for(
        '.broadcast_dashboard_updates',
        service_id=SERVICE_ONE_ID,
    ))

    assert response.status_code == 200

    json_response = json.loads(response.get_data(as_text=True))

    assert json_response.keys() == {
        'pending_approval_broadcasts',
        'live_broadcasts',
        'previous_broadcasts',
    }

    assert 'Prepared by Test User' in json_response['pending_approval_broadcasts']
    assert 'Live until tomorrow at 2:20am' in json_response['live_broadcasts']
    assert 'Finished yesterday at 8:20pm' in json_response['previous_broadcasts']


def test_broadcast_page(
    client_request,
    service_one,
    fake_uuid,
    mock_create_broadcast_message,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.broadcast',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_redirect=url_for(
            '.preview_broadcast_areas',
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
            _external=True,
        ),
    ),


def test_preview_broadcast_areas_page(
    client_request,
    service_one,
    fake_uuid,
    mock_get_draft_broadcast_message,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.preview_broadcast_areas',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


def test_choose_broadcast_library_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    page = client_request.get(
        '.choose_broadcast_library',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert [
        normalize_spaces(title.text)
        for title in page.select('.file-list-filename-large')
    ] == [
        'Countries',
        'Local authorities',
    ]

    assert normalize_spaces(page.select('.file-list-hint-large')[0].text) == (
        'England, Northern Ireland, Scotland, and Wales'
    )

    assert page.select_one('a.file-list-filename-large.govuk-link')['href'] == url_for(
        '.choose_broadcast_area',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug='ctry19',
    )


def test_choose_broadcast_area_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    page = client_request.get(
        '.choose_broadcast_area',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug='ctry19',
    )
    assert normalize_spaces(page.select_one('h1').text) == (
        'Choose countries'
    )
    assert [
        (
            choice.select_one('input')['value'],
            normalize_spaces(choice.select_one('label').text),
        )
        for choice in page.select('form[method=post] .govuk-checkboxes__item')
    ] == [
        ('ctry19-E92000001', 'England'),
        ('ctry19-N92000002', 'Northern Ireland'),
        ('ctry19-S92000003', 'Scotland'),
        ('ctry19-W92000004', 'Wales'),
    ]


def test_choose_broadcast_area_page_for_area_with_sub_areas(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    page = client_request.get(
        '.choose_broadcast_area',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug='wd20-lad20',
    )
    assert normalize_spaces(page.select_one('h1').text) == (
        'Choose a local authority'
    )
    live_search = page.select_one("[data-module=live-search]")
    assert live_search['data-targets'] == '.file-list-item'
    assert live_search.select_one('input')['type'] == 'search'
    partial_url_for = partial(
        url_for,
        'main.choose_broadcast_sub_area',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug='wd20-lad20',
    )
    choices = [
        (
            choice.select_one('a.file-list-filename-large')['href'],
            normalize_spaces(choice.text),
        )
        for choice in page.select('.file-list-item')
    ]
    assert len(choices) == 379
    assert choices[:2] == [
        (
            partial_url_for(area_slug='lad20-S12000033'),
            'Aberdeen City',
        ),
        (
            partial_url_for(area_slug='lad20-S12000034'),
            'Aberdeenshire',
        ),
    ]
    assert choices[-1:] == [
        (
            partial_url_for(area_slug='lad20-E06000014'),
            'York',
        ),
    ]


def test_choose_broadcast_sub_area_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    page = client_request.get(
        'main.choose_broadcast_sub_area',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug='wd20-lad20',
        area_slug='lad20-S12000033',
    )
    assert normalize_spaces(page.select_one('h1').text) == (
        'Choose an area of Aberdeen City'
    )
    live_search = page.select_one("[data-module=live-search]")
    assert live_search['data-targets'] == '.govuk-checkboxes__item'
    assert live_search.select_one('input')['type'] == 'search'
    choices = [
        (
            choice.select_one('input')['value'],
            normalize_spaces(choice.select_one('label').text),
        )
        for choice in page.select('form[method=post] .govuk-checkboxes__item')
    ]
    assert choices[:3] == [
        ('y', 'All of Aberdeen City'),
        ('wd20-S13002845', 'Airyhall/Broomhill/Garthdee'),
        ('wd20-S13002836', 'Bridge of Don'),
    ]
    assert choices[-1:] == [
        ('wd20-S13002846', 'Torry/Ferryhill'),
    ]


def test_add_broadcast_area(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    client_request.post(
        '.choose_broadcast_area',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug='ctry19',
        _data={
            'areas': ['ctry19-E92000001', 'ctry19-W92000004']
        }
    )
    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            'areas': ['ctry19-E92000001', 'ctry19-S92000003', 'ctry19-W92000004']
        },
    )


@pytest.mark.parametrize('post_data, expected_selected', (
    ({
        'select_all': 'y',
        'areas': [
            'wd20-S13002845',
        ]
    }, [
        'lad20-S12000033',
        # wd20-S13002845 is ignored because the user chose ‘Select all…’
    ]),
    ({
        'areas': [
            'wd20-S13002845',
            'wd20-S13002836',
        ]
    }, [
        'wd20-S13002845',
        'wd20-S13002836',
    ]),
))
def test_add_broadcast_sub_area(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    post_data,
    expected_selected,
):
    service_one['permissions'] += ['broadcast']
    client_request.post(
        '.choose_broadcast_sub_area',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug='wd20-lad20',
        area_slug='lad20-S12000033',
        _data=post_data,
    )
    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            'areas': [
                # These two areas are on the broadcast already
                'ctry19-E92000001',
                'ctry19-S92000003',
            ] + expected_selected
        },
    )


def test_remove_broadcast_area_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.remove_broadcast_area',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        area_slug='ctry19-E92000001',
        _expected_redirect=url_for(
            '.preview_broadcast_areas',
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
            _external=True,
        ),
    )
    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            'areas': ['ctry19-S92000003']
        },
    )


def test_preview_broadcast_message_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_get_broadcast_template,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']

    page = client_request.get(
        '.preview_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert [
        normalize_spaces(area.text)
        for area in page.select('.area-list-item.area-list-item--unremoveable')
    ] == [
        'England',
        'Scotland',
    ]

    assert normalize_spaces(
        page.select_one('.broadcast-message-wrapper').text
    ) == (
        'This is a test'
    )

    form = page.select_one('form')
    assert form['method'] == 'post'
    assert 'action' not in form


@freeze_time('2020-02-02 02:02:02')
def test_start_broadcasting(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_get_broadcast_template,
    mock_update_broadcast_message_status,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    client_request.post(
        '.preview_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=url_for(
            'main.view_broadcast_message',
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
            _external=True,
        ),
    ),
    mock_update_broadcast_message_status.assert_called_once_with(
        'pending-approval',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


@pytest.mark.parametrize('extra_fields, expected_paragraphs', (
    ({
        'status': 'broadcasting',
        'finishes_at': '2020-02-23T23:23:23.000000',
    }, [
        'Created by Alice and approved by Bob.',
        'Started broadcasting on 20 February at 8:20pm.',
        'Live until tomorrow at 11:23pm Stop broadcast early',
    ]),
    ({
        'status': 'broadcasting',
        'finishes_at': '2020-02-22T22:20:20.000000',  # 2 mins before now()
    }, [
        'Created by Alice and approved by Bob.',
        'Started broadcasting on 20 February at 8:20pm.',
        'Finished broadcasting today at 10:20pm.',
    ]),
    ({
        'status': 'finished',
        'finishes_at': '2020-02-21T21:21:21.000000',
    }, [
        'Created by Alice and approved by Bob.',
        'Started broadcasting on 20 February at 8:20pm.',
        'Finished broadcasting yesterday at 9:21pm.',
    ]),
    ({
        'status': 'cancelled',
        'cancelled_by_id': sample_uuid,
        'cancelled_at': '2020-02-21T21:21:21.000000',
    }, [
        'Created by Alice and approved by Bob.',
        'Started broadcasting on 20 February at 8:20pm.',
        'Stopped by Carol yesterday at 9:21pm.',
    ]),
))
@freeze_time('2020-02-22T22:22:22.000000')
def test_view_broadcast_message_page(
    mocker,
    client_request,
    service_one,
    active_user_with_permissions,
    mock_get_broadcast_template,
    fake_uuid,
    extra_fields,
    expected_paragraphs,
):
    mocker.patch(
        'app.broadcast_message_api_client.get_broadcast_message',
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            approved_by_id=fake_uuid,
            starts_at='2020-02-20T20:20:20.000000',
            **extra_fields
        ),
    )
    mocker.patch('app.user_api_client.get_user', side_effect=[
        active_user_with_permissions,
        user_json(name='Alice'),
        user_json(name='Bob'),
        user_json(name='Carol'),
    ])
    service_one['permissions'] += ['broadcast']

    page = client_request.get(
        '.view_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert [
        normalize_spaces(p.text) for p in page.select('main p.govuk-body')
    ] == expected_paragraphs


@freeze_time('2020-02-22T22:22:22.000000')
def test_view_pending_broadcast(
    mocker,
    client_request,
    service_one,
    active_user_with_permissions,
    mock_get_broadcast_template,
    fake_uuid,
):
    mocker.patch(
        'app.broadcast_message_api_client.get_broadcast_message',
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at='2020-02-23T23:23:23.000000',
            status='pending-approval',
        ),
    )
    mocker.patch('app.user_api_client.get_user', side_effect=[
        active_user_with_permissions,  # Current user
        user_json(id_=uuid.uuid4()),  # User who created broadcast
    ])
    service_one['permissions'] += ['broadcast']

    page = client_request.get(
        '.view_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert (
        normalize_spaces(page.select_one('.banner').text)
    ) == (
        'Test User wants to broadcast this message until tomorrow at 11:23pm. '
        'Start broadcasting now Reject this broadcast'
    )

    form = page.select_one('form.banner')
    assert form['method'] == 'post'
    assert 'action' not in form
    assert form.select_one('button[type=submit]')

    link = form.select_one('a.govuk-link.govuk-link--destructive')
    assert link.text == 'Reject this broadcast'
    assert link['href'] == url_for(
        '.reject_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


@freeze_time('2020-02-22T22:22:22.000000')
def test_cant_approve_own_broadcast(
    mocker,
    client_request,
    service_one,
    active_user_with_permissions,
    mock_get_broadcast_template,
    fake_uuid,
):
    mocker.patch(
        'app.broadcast_message_api_client.get_broadcast_message',
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at='2020-02-23T23:23:23.000000',
            status='pending-approval',
        ),
    )
    mocker.patch('app.user_api_client.get_user', side_effect=[
        active_user_with_permissions,  # Current user
        active_user_with_permissions,  # User who created broadcast (the same)
    ])
    service_one['permissions'] += ['broadcast']

    page = client_request.get(
        '.view_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert (
        normalize_spaces(page.select_one('.banner').text)
    ) == (
        'Your broadcast is waiting for approval from another member of your team '
        'Once approved it will be live until tomorrow at 11:23pm '
        'Withdraw this broadcast'
    )

    assert not page.select_one('form')

    link = page.select_one('.banner a.govuk-link.govuk-link--destructive')
    assert link.text == 'Withdraw this broadcast'
    assert link['href'] == url_for(
        '.reject_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


@freeze_time('2020-02-22T22:22:22.000000')
def test_view_only_user_cant_approve_broadcast(
    mocker,
    client_request,
    service_one,
    active_user_with_permissions,
    active_user_view_permissions,
    mock_get_broadcast_template,
    fake_uuid,
):
    mocker.patch(
        'app.broadcast_message_api_client.get_broadcast_message',
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at='2020-02-23T23:23:23.000000',
            status='pending-approval',
        ),
    )
    mocker.patch('app.user_api_client.get_user', side_effect=[
        active_user_view_permissions,  # Current user
        active_user_with_permissions,  # User who created broadcast
    ])
    service_one['permissions'] += ['broadcast']

    page = client_request.get(
        '.view_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert (
        normalize_spaces(page.select_one('.banner').text)
    ) == (
        'This broadcast is waiting for approval '
        'You don’t have permission to approve broadcasts.'
    )

    assert not page.select_one('form')
    assert not page.select_one('.banner a')


@pytest.mark.parametrize('initial_status, expected_approval', (
    ('draft', False,),
    ('pending-approval', True),
    ('rejected', False),
    ('broadcasting', False),
    ('cancelled', False),
))
@freeze_time('2020-02-22T22:22:22.000000')
def test_approve_broadcast(
    mocker,
    client_request,
    service_one,
    mock_get_broadcast_template,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status,
    initial_status,
    expected_approval,
):
    mocker.patch(
        'app.broadcast_message_api_client.get_broadcast_message',
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at='2020-02-23T23:23:23.000000',
            status=initial_status,
        ),
    )
    service_one['permissions'] += ['broadcast']

    client_request.post(
        '.view_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=url_for(
            '.view_broadcast_message',
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
            _external=True,
        )
    )

    if expected_approval:
        mock_update_broadcast_message.assert_called_once_with(
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
            data={
                'starts_at': '2020-02-22T22:22:22',
                'finishes_at': '2020-02-23T22:21:22',
            },
        )
        mock_update_broadcast_message_status.assert_called_once_with(
            'broadcasting',
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
        )
    else:
        assert mock_update_broadcast_message.called is False
        assert mock_update_broadcast_message_status.called is False


@freeze_time('2020-02-22T22:22:22.000000')
def test_reject_broadcast(
    mocker,
    client_request,
    service_one,
    mock_get_broadcast_template,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status,
):
    mocker.patch(
        'app.broadcast_message_api_client.get_broadcast_message',
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at='2020-02-23T23:23:23.000000',
            status='pending-approval',
        ),
    )
    service_one['permissions'] += ['broadcast']

    client_request.get(
        '.reject_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=url_for(
            '.broadcast_dashboard',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )

    assert mock_update_broadcast_message.called is False

    mock_update_broadcast_message_status.assert_called_once_with(
        'rejected',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


@pytest.mark.parametrize('initial_status', (
    'draft',
    'rejected',
    'broadcasting',
    'cancelled',
))
@freeze_time('2020-02-22T22:22:22.000000')
def test_cant_reject_broadcast_in_wrong_state(
    mocker,
    client_request,
    service_one,
    mock_get_broadcast_template,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status,
    initial_status,
):
    mocker.patch(
        'app.broadcast_message_api_client.get_broadcast_message',
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at='2020-02-23T23:23:23.000000',
            status=initial_status,
        ),
    )
    service_one['permissions'] += ['broadcast']

    client_request.get(
        '.reject_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=url_for(
            '.view_broadcast_message',
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
            _external=True,
        )
    )

    assert mock_update_broadcast_message.called is False
    assert mock_update_broadcast_message_status.called is False


def test_no_view_page_for_draft(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.view_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_status=404,
    )


def test_cancel_broadcast(
    client_request,
    service_one,
    mock_get_live_broadcast_message,
    mock_get_broadcast_template,
    mock_update_broadcast_message_status,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    page = client_request.get(
        '.cancel_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )
    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        'Are you sure you want to stop this broadcast now? '
        'Yes, stop broadcasting'
    )
    form = page.select_one('form')
    assert form['method'] == 'post'
    assert 'action' not in form
    assert normalize_spaces(form.select_one('button[type=submit]').text) == (
        'Yes, stop broadcasting'
    )
    assert mock_update_broadcast_message_status.called is False
    assert url_for(
        '.cancel_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    ) not in page


def test_confirm_cancel_broadcast(
    client_request,
    service_one,
    mock_get_live_broadcast_message,
    mock_get_broadcast_template,
    mock_update_broadcast_message_status,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    client_request.post(
        '.cancel_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=url_for(
            '.view_broadcast_message',
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
            _external=True,
        ),
    )
    mock_update_broadcast_message_status.assert_called_once_with(
        'cancelled',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


@pytest.mark.parametrize('method', ('post', 'get'))
def test_cant_cancel_broadcast_in_a_different_state(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message_status,
    fake_uuid,
    method,
):
    service_one['permissions'] += ['broadcast']
    getattr(client_request, method)(
        '.cancel_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=url_for(
            '.view_broadcast_message',
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
            _external=True,
        ),
    )
    assert mock_update_broadcast_message_status.called is False
