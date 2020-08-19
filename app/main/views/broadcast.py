from flask import (
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from app import current_service
from app.main import main
from app.main.forms import (
    BroadcastAreaForm,
    BroadcastAreaFormWithSelectAll,
    SearchByNameForm,
)
from app.models.broadcast_message import BroadcastMessage, BroadcastMessages
from app.utils import service_has_permission, user_has_permissions


@main.route('/services/<uuid:service_id>/broadcast-tour/<int:step_index>')
@user_has_permissions()
@service_has_permission('broadcast')
def broadcast_tour(service_id, step_index):
    if step_index not in (1, 2, 3):
        abort(404)
    return render_template(
        f'views/broadcast/tour/{step_index}.html'
    )


@main.route('/services/<uuid:service_id>/broadcast-dashboard')
@user_has_permissions()
@service_has_permission('broadcast')
def broadcast_dashboard(service_id):
    return render_template(
        'views/broadcast/dashboard.html',
        partials=get_broadcast_dashboard_partials(current_service.id),
    )


@main.route('/services/<uuid:service_id>/broadcast-dashboard.json')
@user_has_permissions()
@service_has_permission('broadcast')
def broadcast_dashboard_updates(service_id):
    return jsonify(get_broadcast_dashboard_partials(current_service.id))


def get_broadcast_dashboard_partials(service_id):
    broadcast_messages = BroadcastMessages(service_id)
    return dict(
        pending_approval_broadcasts=render_template(
            'views/broadcast/partials/dashboard-table.html',
            broadcasts=broadcast_messages.with_status('pending-approval'),
            empty_message='You do not have any broadcasts waiting for approval',
        ),
        live_broadcasts=render_template(
            'views/broadcast/partials/dashboard-table.html',
            broadcasts=broadcast_messages.with_status('broadcasting'),
            empty_message='You do not have any live broadcasts at the moment',
        ),
        previous_broadcasts=render_template(
            'views/broadcast/partials/dashboard-table.html',
            broadcasts=broadcast_messages.with_status('cancelled', 'completed'),
            empty_message='You do not have any previous broadcasts',
        ),
    )


@main.route('/services/<uuid:service_id>/new-broadcast/<uuid:template_id>')
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def broadcast(service_id, template_id):
    return redirect(url_for(
        '.preview_broadcast_areas',
        service_id=current_service.id,
        broadcast_message_id=BroadcastMessage.create(
            service_id=service_id,
            template_id=template_id,
        ).id,
    ))


@main.route('/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/areas')
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def preview_broadcast_areas(service_id, broadcast_message_id):
    return render_template(
        'views/broadcast/preview-areas.html',
        broadcast_message=BroadcastMessage.from_id(
            broadcast_message_id,
            service_id=current_service.id,
        ),
    )


@main.route('/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/libraries')
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def choose_broadcast_library(service_id, broadcast_message_id):
    return render_template(
        'views/broadcast/libraries.html',
        libraries=BroadcastMessage.libraries,
        broadcast_message_id=broadcast_message_id,
    )


@main.route(
    '/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/libraries/<library_slug>',
    methods=['GET', 'POST'],
)
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def choose_broadcast_area(service_id, broadcast_message_id, library_slug):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    library = BroadcastMessage.libraries.get(library_slug)

    if library.is_group:
        return render_template(
            'views/broadcast/areas-with-sub-areas.html',
            search_form=SearchByNameForm(),
            show_search_form=(len(library) > 7),
            library=library,
            page_title=f'Choose a {library.name_singular.lower()}',
            broadcast_message=broadcast_message,
        )

    form = BroadcastAreaForm.from_library(library)
    if form.validate_on_submit():
        broadcast_message.add_areas(*form.areas.data)
        return redirect(url_for(
            '.preview_broadcast_areas',
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        ))
    return render_template(
        'views/broadcast/areas.html',
        form=form,
        search_form=SearchByNameForm(),
        show_search_form=(len(form.areas.choices) > 7),
        page_title=f'Choose {library.name.lower()}',
        broadcast_message=broadcast_message,
    )


@main.route(
    '/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/libraries/<library_slug>/<area_slug>',
    methods=['GET', 'POST'],
)
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def choose_broadcast_sub_area(service_id, broadcast_message_id, library_slug, area_slug):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    area = BroadcastMessage.libraries.get_areas(area_slug)[0]

    form = BroadcastAreaFormWithSelectAll.from_library(
        area.sub_areas,
        select_all_choice=(area.id, f'All of {area.name}'),
    )
    if form.validate_on_submit():
        broadcast_message.add_areas(*form.selected_areas)
        return redirect(url_for(
            '.preview_broadcast_areas',
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        ))
    return render_template(
        'views/broadcast/sub-areas.html',
        form=form,
        search_form=SearchByNameForm(),
        show_search_form=(len(form.areas.choices) > 7),
        library_slug=library_slug,
        page_title=f'Choose an area of {area.name}',
        broadcast_message=broadcast_message,
    )


@main.route('/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/remove/<area_slug>')
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def remove_broadcast_area(service_id, broadcast_message_id, area_slug):
    BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    ).remove_area(
        area_slug
    )
    return redirect(url_for(
        '.preview_broadcast_areas',
        service_id=current_service.id,
        broadcast_message_id=broadcast_message_id,
    ))


@main.route(
    '/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/preview',
    methods=['GET', 'POST'],
)
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def preview_broadcast_message(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    if request.method == 'POST':
        broadcast_message.request_approval()
        return redirect(url_for(
            '.view_broadcast_message',
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        ))

    return render_template(
        'views/broadcast/preview-message.html',
        broadcast_message=broadcast_message,
    )


@main.route('/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>')
@user_has_permissions()
@service_has_permission('broadcast')
def view_broadcast_message(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    if broadcast_message.status == 'draft':
        abort(404)
    return render_template(
        'views/broadcast/view-message.html',
        broadcast_message=broadcast_message,
    )


@main.route('/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>', methods=['POST'])
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def approve_broadcast_message(service_id, broadcast_message_id):

    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    if broadcast_message.status != 'pending-approval':
        return redirect(url_for(
            '.view_broadcast_message',
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        ))

    broadcast_message.approve_broadcast()

    return redirect(url_for(
        '.view_broadcast_message',
        service_id=current_service.id,
        broadcast_message_id=broadcast_message.id,
    ))


@main.route('/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/reject')
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def reject_broadcast_message(service_id, broadcast_message_id):

    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    if broadcast_message.status != 'pending-approval':
        return redirect(url_for(
            '.view_broadcast_message',
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        ))

    broadcast_message.reject_broadcast()

    return redirect(url_for(
        '.broadcast_dashboard',
        service_id=current_service.id,
    ))


@main.route(
    '/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/cancel',
    methods=['GET', 'POST'],
)
@user_has_permissions('send_messages')
@service_has_permission('broadcast')
def cancel_broadcast_message(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    if broadcast_message.status != 'broadcasting':
        return redirect(url_for(
            '.view_broadcast_message',
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        ))

    if request.method == 'POST':
        broadcast_message.cancel_broadcast()
        return redirect(url_for(
            '.view_broadcast_message',
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        ))

    flash([
        'Are you sure you want to stop this broadcast now?'
    ], 'stop broadcasting')

    return render_template(
        'views/broadcast/view-message.html',
        broadcast_message=broadcast_message,
        hide_stop_link=True,
    )
