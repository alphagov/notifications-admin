from flask import redirect, render_template, request, session, url_for
from notifications_utils.broadcast_areas import broadcast_area_libraries
from orderedset import OrderedSet

from app import current_service
from app.main import main
from app.utils import service_has_permission, user_has_permissions


@main.route('/services/<uuid:service_id>/broadcast')
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def broadcast(service_id):
    if 'broadcast_areas' in session:
        session.pop('broadcast_areas')
    return redirect(url_for(
        '.preview_broadcast_areas',
        service_id=current_service.id,
    ))


@main.route('/services/<uuid:service_id>/broadcast/areas')
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def preview_broadcast_areas(service_id):
    selected_areas_ids = session.get('broadcast_areas', [])
    return render_template(
        'views/broadcast/preview-areas.html',
        selected=list(broadcast_area_libraries.get_areas(
            *selected_areas_ids
        )),
        area_polygons=broadcast_area_libraries.get_polygons_for_areas_lat_long(
            *selected_areas_ids
        )
    )


@main.route('/services/<uuid:service_id>/broadcast/libraries')
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def choose_broadcast_library(service_id):
    return render_template(
        'views/broadcast/libraries.html',
        libraries=broadcast_area_libraries,
        selected=broadcast_area_libraries.get_areas(
            *session.get('broadcast_areas', [])
        ),
    )


@main.route('/services/<uuid:service_id>/broadcast/libraries/<library_slug>')
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def choose_broadcast_area(service_id, library_slug):
    return render_template(
        'views/broadcast/areas.html',
        areas=broadcast_area_libraries.get(library_slug),
    )


@main.route('/services/<uuid:service_id>/broadcast/add/<area_slug>')
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def add_broadcast_area(service_id, area_slug):
    if not session.get('broadcast_areas'):
        session['broadcast_areas'] = []

    session['broadcast_areas'].append(area_slug)

    session['broadcast_areas'] = list(OrderedSet(
        session['broadcast_areas']
    ))
    return redirect(url_for(
        '.preview_broadcast_areas',
        service_id=current_service.id,
    ))


@main.route('/services/<uuid:service_id>/broadcast/remove/<area_slug>')
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def remove_broadcast_area(service_id, area_slug):
    session['broadcast_areas'] = list(filter(
        lambda saved_area_id: saved_area_id != area_slug,
        session.get('broadcast_areas', []),
    ))

    return redirect(url_for(
        '.preview_broadcast_areas',
        service_id=current_service.id,
    ))


@main.route('/services/<uuid:service_id>/broadcast/preview', methods=['GET', 'POST'])
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def preview_broadcast_message(service_id):
    if request.method == 'POST':
        return 'OK'
    selected_areas = session.get('broadcast_areas', [])
    return render_template(
        'views/broadcast/preview-message.html',
        selected=list(broadcast_area_libraries.get_areas(
            *selected_areas
        )),
    )
