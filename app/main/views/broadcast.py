from flask import (
    render_template,
    redirect,
    session,
    url_for,
)
from orderedset import OrderedSet

from app import current_service
from app.main import main

from app.models.broadcast_area import broadcast_region_libraries


@main.route("/services/<uuid:service_id>/broadcast")
def broadcast(service_id):
    if 'broadcast_regions' in session:
        session.pop('broadcast_regions')
    return redirect(url_for(
        '.preview_broadcast_regions',
        service_id=current_service.id,
    ))


@main.route("/services/<uuid:service_id>/broadcast/regions")
def preview_broadcast_regions(service_id):
    selected_regions_ids = session.get('broadcast_regions', [])
    return render_template(
        'views/broadcast/preview-regions.html',
        selected=list(broadcast_region_libraries.get_regions(
            *selected_regions_ids
        )),
        area_polygons=broadcast_region_libraries.get_area_polygons_for_regions_lat_long(
            *selected_regions_ids
        )
    )


@main.route("/services/<uuid:service_id>/broadcast/libraries")
def choose_broadcast_library(service_id):
    return render_template(
        'views/broadcast/libraries.html',
        libraries=broadcast_region_libraries,
        selected=broadcast_region_libraries.get_regions(
            *session.get('broadcast_regions', [])
        ),
    )


@main.route("/services/<uuid:service_id>/broadcast/libraries/<library_id>")
def choose_broadcast_region(service_id, library_id):
    return render_template(
        'views/broadcast/regions.html',
        regions=broadcast_region_libraries.get(library_id),
    )


@main.route("/services/<uuid:service_id>/broadcast/add/<region_id>")
def add_broadcast_region(service_id, region_id):
    if not session.get('broadcast_regions'):
        session['broadcast_regions'] = []

    session['broadcast_regions'].append(region_id)
    session['broadcast_regions'] = list(OrderedSet(
        session['broadcast_regions']
    ))
    return redirect(url_for(
        '.preview_broadcast_regions',
        service_id=current_service.id,
    ))


@main.route("/services/<uuid:service_id>/broadcast/remove/<region_id>")
def remove_broadcast_region(service_id, region_id):
    session['broadcast_regions'] = list(filter(
        lambda saved_region_id: saved_region_id != region_id,
        session.get('broadcast_regions', []),
    ))

    return redirect(url_for(
        '.preview_broadcast_regions',
        service_id=current_service.id,
    ))


@main.route("/services/<uuid:service_id>/broadcast/send")
def send_to_broadcast_region(service_id):
    selected_regions_ids = session.get('broadcast_regions', [])

    area_polygons = broadcast_region_libraries.get_area_polygons_for_regions_lat_long(
        *selected_regions_ids
    )
    return '<br><br>'.join(
        (
            '{} ({} points)'.format(
                polygon[:5], len(polygon)
            )
            for polygon in area_polygons)
    )

    return str(area_polygons)
