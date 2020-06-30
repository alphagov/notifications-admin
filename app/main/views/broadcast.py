from flask import (
    render_template,
    redirect,
    session,
    url_for,
)
from orderedset import OrderedSet

from app import current_service
from app.main.forms import BroadcastRegionForm, SearchByNameForm
from app.main import main

from app.models.broadcast_area import broadcast_region_libraries
from app.utils import user_has_permissions, service_has_permission


@main.route("/services/<uuid:service_id>/broadcast")
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def broadcast(service_id):
    if 'broadcast_regions' in session:
        session.pop('broadcast_regions')
    return redirect(url_for(
        '.preview_broadcast_regions',
        service_id=current_service.id,
    ))


@main.route("/services/<uuid:service_id>/broadcast/regions")
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
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
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def choose_broadcast_library(service_id):
    return render_template(
        'views/broadcast/libraries.html',
        libraries=broadcast_region_libraries,
        selected=broadcast_region_libraries.get_regions(
            *session.get('broadcast_regions', [])
        ),
    )


@main.route("/services/<uuid:service_id>/broadcast/libraries/<library_id>", methods=['GET', 'POST'])
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def choose_broadcast_region(service_id, library_id):
    library = broadcast_region_libraries.get(library_id)
    form = BroadcastRegionForm.from_library(library)
    if form.validate_on_submit():
        if not session.get('broadcast_regions'):
            session['broadcast_regions'] = []
        session['broadcast_regions'] = session['broadcast_regions'] + form.regions.data
        session['broadcast_regions'] = list(OrderedSet(
            session['broadcast_regions']
        ))
        return redirect(url_for(
            '.preview_broadcast_regions',
            service_id=current_service.id,
        ))
    return render_template(
        'views/broadcast/regions.html',
        form=form,
        search_form=SearchByNameForm(),
        page_title=library.name,
    )


@main.route("/services/<uuid:service_id>/broadcast/remove/<region_id>")
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def remove_broadcast_region(service_id, region_id):
    session['broadcast_regions'] = list(filter(
        lambda saved_region_id: saved_region_id != region_id,
        session.get('broadcast_regions', []),
    ))

    return redirect(url_for(
        '.preview_broadcast_regions',
        service_id=current_service.id,
    ))


@main.route("/services/<uuid:service_id>/broadcast/preview")
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def preview_broadcast_message(service_id):
    selected_regions_ids = session.get('broadcast_regions', [])
    return render_template(
        'views/broadcast/preview-message.html',
        selected=list(broadcast_region_libraries.get_regions(
            *selected_regions_ids
        )),
    )


@main.route("/services/<uuid:service_id>/broadcast/send")
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
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
