import pytest
from flask import url_for

from tests.conftest import SERVICE_ONE_ID


@pytest.mark.parametrize('endpoint, extra_args', (
    ('.broadcast_dashboard', {}),
    ('.broadcast', {}),
    ('.preview_broadcast_areas', {}),
    ('.choose_broadcast_library', {}),
    ('.choose_broadcast_area', {'library_slug': 'countries'}),
    ('.remove_broadcast_area', {'area_slug': 'england'}),
    ('.preview_broadcast_message', {}),
))
def test_broadcast_pages_403_without_permission(
    client_request,
    endpoint,
    extra_args,
):
    client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
        **extra_args
    )


def test_broadcast_dashboard(
    client_request,
    service_one,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.broadcast_dashboard',
        service_id=SERVICE_ONE_ID,
    ),


def test_broadcast_page(
    client_request,
    service_one,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.broadcast',
        service_id=SERVICE_ONE_ID,
        _expected_redirect=url_for(
            '.preview_broadcast_areas',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    ),


def test_preview_broadcast_areas_page(
    client_request,
    service_one,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.preview_broadcast_areas',
        service_id=SERVICE_ONE_ID,
    )


def test_choose_broadcast_library_page(
    client_request,
    service_one,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.choose_broadcast_library',
        service_id=SERVICE_ONE_ID,
    )


def test_choose_broadcast_area_page(
    client_request,
    service_one,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.choose_broadcast_area',
        service_id=SERVICE_ONE_ID,
        library_slug='countries',
    )


def test_remove_broadcast_area_page(
    client_request,
    service_one,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.remove_broadcast_area',
        service_id=SERVICE_ONE_ID,
        area_slug='england',
        _expected_redirect=url_for(
            '.preview_broadcast_areas',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    ),


def test_preview_broadcast_message_page(
    client_request,
    service_one,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.preview_broadcast_message',
        service_id=SERVICE_ONE_ID,
    ),
