from flask import (
    render_template,
    redirect,
    session,
    url_for,
)
from orderedset import OrderedSet

from app.main import main

from app.models.broadcast_area import broadcast_region_libraries


@main.route("/broadcast")
def broadcast():
    session.pop('broadcast_regions')
    return redirect(url_for('.preview_broadcast_regions'))


@main.route("/broadcast/regions")
def preview_broadcast_regions():
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


@main.route("/broadcast/libraries")
def choose_broadcast_library():
    return render_template(
        'views/broadcast/libraries.html',
        libraries=broadcast_region_libraries,
        selected=broadcast_region_libraries.get_regions(
            *session.get('broadcast_regions', [])
        ),
    )


@main.route("/broadcast/libraries/<library_id>")
def choose_broadcast_region(library_id):
    return render_template(
        'views/broadcast/regions.html',
        regions=broadcast_region_libraries.get(library_id),
    )


@main.route("/broadcast/add/<region_id>")
def add_broadcast_region(region_id):
    if not session.get('broadcast_regions'):
        session['broadcast_regions'] = []

    session['broadcast_regions'].append(region_id)
    session['broadcast_regions'] = list(OrderedSet(
        session['broadcast_regions']
    ))
    return redirect(url_for(
        '.preview_broadcast_regions'
    ))


@main.route("/broadcast/remove/<region_id>")
def remove_broadcast_region(region_id):
    session['broadcast_regions'] = list(filter(
        lambda saved_region_id: saved_region_id != region_id,
        session.get('broadcast_regions', []),
    ))

    return redirect(url_for(
        '.preview_broadcast_regions'
    ))


@main.route("/broadcast/send")
def send_to_broadcast_region():
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
