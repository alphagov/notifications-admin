from flask import (
    render_template,
    redirect,
    session,
    url_for,
)

from app.main import main

from app.models.broadcast_area import broadcast_region_libraries


@main.route("/broadcast")
def choose_broadcast_library():
    return render_template(
        'views/broadcast/libraries.html',
        libraries=broadcast_region_libraries,
        selected=broadcast_region_libraries.get_regions(
            *session.get('broadcast_regions', [])
        ),
    )


@main.route("/broadcast/<library>")
def choose_broadcast_region(library):
    return render_template(
        'views/broadcast/regions.html',
        regions=broadcast_region_libraries.get(library),
    )


@main.route("/broadcast/add/<region_id>")
def add_broadcast_region(region_id):
    if not session.get('broadcast_regions'):
        session['broadcast_regions'] = []

    session['broadcast_regions'].append(region_id)
    return redirect(url_for(
        '.choose_broadcast_library'
    ))


@main.route("/broadcast/remove/<region_id>")
def remove_broadcast_region(region_id):
    session['broadcast_regions'] = list(filter(
        lambda saved_region_id: saved_region_id != region_id,
        session.get('broadcast_regions', []),
    ))

    return redirect(url_for(
        '.choose_broadcast_library'
    ))
