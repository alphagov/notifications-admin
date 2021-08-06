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
    BroadcastTemplateForm,
    ConfirmBroadcastForm,
    NewBroadcastForm,
    SearchByNameForm,
)
from app.models.broadcast_message import BroadcastMessage, BroadcastMessages
from app.utils import service_has_permission
from app.utils.user import user_has_permissions


def _get_back_link_from_view_broadcast_endpoint():
    return {
        'main.view_current_broadcast': '.broadcast_dashboard',
        'main.view_previous_broadcast': '.broadcast_dashboard_previous',
        'main.view_rejected_broadcast': '.broadcast_dashboard_rejected',
        'main.approve_broadcast_message': '.broadcast_dashboard',
    }[request.endpoint]


@main.route('/services/<uuid:service_id>/broadcast-tour/<int:step_index>')
@user_has_permissions()
@service_has_permission('broadcast')
def broadcast_tour(service_id, step_index):
    if step_index not in (1, 2, 3, 4, 5, 6):
        abort(404)
    return render_template(
        f'views/broadcast/tour/{step_index}.html'
    )


@main.route('/services/<uuid:service_id>/broadcast-tour/live/<int:step_index>')
@user_has_permissions()
@service_has_permission('broadcast')
def broadcast_tour_live(service_id, step_index):
    if step_index not in (1, 2):
        abort(404)
    return render_template(
        f'views/broadcast/tour/live/{step_index}.html'
    )


@main.route('/services/<uuid:service_id>/current-alerts')
@user_has_permissions()
@service_has_permission('broadcast')
def broadcast_dashboard(service_id):
    return render_template(
        'views/broadcast/dashboard.html',
        partials=get_broadcast_dashboard_partials(current_service.id),
    )


@main.route('/services/<uuid:service_id>/past-alerts')
@user_has_permissions()
@service_has_permission('broadcast')
def broadcast_dashboard_previous(service_id):
    return render_template(
        'views/broadcast/previous-broadcasts.html',
        broadcasts=BroadcastMessages(service_id).with_status(
            'cancelled',
            'completed',
        ),
        page_title='Past alerts',
        empty_message='You do not have any past alerts',
        view_broadcast_endpoint='.view_previous_broadcast',
    )


@main.route('/services/<uuid:service_id>/rejected-alerts')
@user_has_permissions()
@service_has_permission('broadcast')
def broadcast_dashboard_rejected(service_id):
    return render_template(
        'views/broadcast/previous-broadcasts.html',
        broadcasts=BroadcastMessages(service_id).with_status(
            'rejected',
        ),
        page_title='Rejected alerts',
        empty_message='You do not have any rejected alerts',
        view_broadcast_endpoint='.view_rejected_broadcast',
    )


@main.route('/services/<uuid:service_id>/broadcast-dashboard.json')
@user_has_permissions()
@service_has_permission('broadcast')
def broadcast_dashboard_updates(service_id):
    return jsonify(get_broadcast_dashboard_partials(current_service.id))


def get_broadcast_dashboard_partials(service_id):
    broadcast_messages = BroadcastMessages(service_id)
    return dict(
        current_broadcasts=render_template(
            'views/broadcast/partials/dashboard-table.html',
            broadcasts=broadcast_messages.with_status('pending-approval', 'broadcasting'),
            empty_message='You do not have any current alerts',
            view_broadcast_endpoint='.view_current_broadcast',
        ),
    )


@main.route('/services/<uuid:service_id>/new-broadcast', methods=['GET', 'POST'])
@user_has_permissions('create_broadcasts', restrict_admin_usage=True)
@service_has_permission('broadcast')
def new_broadcast(service_id):
    form = NewBroadcastForm()

    if form.validate_on_submit():
        if form.use_template:
            return redirect(url_for(
                '.choose_template',
                service_id=current_service.id,
            ))
        return redirect(url_for(
            '.write_new_broadcast',
            service_id=current_service.id,
        ))

    return render_template(
        'views/broadcast/new-broadcast.html',
        form=form,
    )


@main.route('/services/<uuid:service_id>/write-new-broadcast', methods=['GET', 'POST'])
@user_has_permissions('create_broadcasts', restrict_admin_usage=True)
@service_has_permission('broadcast')
def write_new_broadcast(service_id):
    form = BroadcastTemplateForm()

    if form.validate_on_submit():
        broadcast_message = BroadcastMessage.create_from_content(
            service_id=current_service.id,
            content=form.template_content.data,
            reference=form.name.data,
        )
        return redirect(url_for(
            '.choose_broadcast_library',
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        ))

    return render_template(
        'views/broadcast/write-new-broadcast.html',
        form=form,
    )


@main.route('/services/<uuid:service_id>/new-broadcast/<uuid:template_id>')
@user_has_permissions('create_broadcasts', restrict_admin_usage=True)
@service_has_permission('broadcast')
def broadcast(service_id, template_id):
    return redirect(url_for(
        '.choose_broadcast_library',
        service_id=current_service.id,
        broadcast_message_id=BroadcastMessage.create(
            service_id=service_id,
            template_id=template_id,
        ).id,
    ))


@main.route('/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/areas')
@user_has_permissions('create_broadcasts', restrict_admin_usage=True)
@service_has_permission('broadcast')
def preview_broadcast_areas(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    if broadcast_message.template_id:
        back_link = url_for(
            '.view_template',
            service_id=current_service.id,
            template_id=broadcast_message.template_id,
        )
    else:
        back_link = url_for(
            '.write_new_broadcast',
            service_id=current_service.id,
        )

    return render_template(
        'views/broadcast/preview-areas.html',
        broadcast_message=broadcast_message,
        back_link=back_link,
    )


@main.route('/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/libraries')
@user_has_permissions('create_broadcasts', restrict_admin_usage=True)
@service_has_permission('broadcast')
def choose_broadcast_library(service_id, broadcast_message_id):
    return render_template(
        'views/broadcast/libraries.html',
        libraries=BroadcastMessage.libraries,
        broadcast_message=BroadcastMessage.from_id(
            broadcast_message_id,
            service_id=current_service.id,
        ),
    )


@main.route(
    '/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/libraries/<library_slug>',
    methods=['GET', 'POST'],
)
@user_has_permissions('create_broadcasts', restrict_admin_usage=True)
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


def _get_broadcast_sub_area_back_link(service_id, broadcast_message_id, library_slug):
    prev_area_slug = request.args.get('prev_area_slug')
    if prev_area_slug:
        return url_for(
            '.choose_broadcast_sub_area',
            service_id=service_id,
            broadcast_message_id=broadcast_message_id,
            library_slug=library_slug,
            area_slug=prev_area_slug,
        )
    else:
        return url_for(
            '.choose_broadcast_area',
            service_id=service_id,
            broadcast_message_id=broadcast_message_id,
            library_slug=library_slug,
        )


@main.route(
    '/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/libraries/<library_slug>/<area_slug>',
    methods=['GET', 'POST'],
)
@user_has_permissions('create_broadcasts', restrict_admin_usage=True)
@service_has_permission('broadcast')
def choose_broadcast_sub_area(service_id, broadcast_message_id, library_slug, area_slug):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    area = BroadcastMessage.libraries.get_areas([area_slug])[0]

    back_link = _get_broadcast_sub_area_back_link(service_id, broadcast_message_id, library_slug)

    is_county = any(sub_area.sub_areas for sub_area in area.sub_areas)

    form = BroadcastAreaFormWithSelectAll.from_library(
        [] if is_county else area.sub_areas,
        select_all_choice=(area.id, f'All of {area.name}'),
    )
    if form.validate_on_submit():
        broadcast_message.add_areas(*form.selected_areas)
        return redirect(url_for(
            '.preview_broadcast_areas',
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        ))

    if is_county:
        # area = county. sub_areas = districts. they have wards, so link to individual district pages
        return render_template(
            'views/broadcast/counties.html',
            form=form,
            search_form=SearchByNameForm(),
            show_search_form=(len(area.sub_areas) > 7),
            library_slug=library_slug,
            page_title=f'Choose an area of {area.name}',
            broadcast_message=broadcast_message,
            county=area,
            back_link=back_link,
        )

    return render_template(
        'views/broadcast/sub-areas.html',
        form=form,
        search_form=SearchByNameForm(),
        show_search_form=(len(form.areas.choices) > 7),
        library_slug=library_slug,
        page_title=f'Choose an area of {area.name}',
        broadcast_message=broadcast_message,
        back_link=back_link,
    )


@main.route('/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/remove/<area_slug>')
@user_has_permissions('create_broadcasts', restrict_admin_usage=True)
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
@user_has_permissions('create_broadcasts', restrict_admin_usage=True)
@service_has_permission('broadcast')
def preview_broadcast_message(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    if request.method == 'POST':
        broadcast_message.request_approval()
        return redirect(url_for(
            '.view_current_broadcast',
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        ))

    return render_template(
        'views/broadcast/preview-message.html',
        broadcast_message=broadcast_message,
    )


@main.route(
    '/services/<uuid:service_id>/current-alerts/<uuid:broadcast_message_id>',
    endpoint='view_current_broadcast',
)
@main.route(
    '/services/<uuid:service_id>/previous-alerts/<uuid:broadcast_message_id>',
    endpoint='view_previous_broadcast',
)
@main.route(
    '/services/<uuid:service_id>/rejected-alerts/<uuid:broadcast_message_id>',
    endpoint='view_rejected_broadcast',
)
@user_has_permissions()
@service_has_permission('broadcast')
def view_broadcast(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    if broadcast_message.status == 'draft':
        abort(404)

    for statuses, endpoint in (
        ({'completed', 'cancelled'}, 'main.view_previous_broadcast'),
        ({'broadcasting', 'pending-approval'}, 'main.view_current_broadcast'),
        ({'rejected'}, 'main.view_rejected_broadcast'),
    ):
        if (
            broadcast_message.status in statuses
            and request.endpoint != endpoint
        ):
            return redirect(url_for(
                endpoint,
                service_id=current_service.id,
                broadcast_message_id=broadcast_message.id,
            ))

    return render_template(
        'views/broadcast/view-message.html',
        broadcast_message=broadcast_message,
        back_link=url_for(
            _get_back_link_from_view_broadcast_endpoint(),
            service_id=current_service.id,
        ),
        form=ConfirmBroadcastForm(
            service_is_live=current_service.live,
            channel=current_service.broadcast_channel,
            max_phones=broadcast_message.count_of_phones_likely,
        ),
    )


@main.route('/services/<uuid:service_id>/current-alerts/<uuid:broadcast_message_id>', methods=['POST'])
@user_has_permissions('approve_broadcasts', restrict_admin_usage=True)
@service_has_permission('broadcast')
def approve_broadcast_message(service_id, broadcast_message_id):

    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    form = ConfirmBroadcastForm(
        service_is_live=current_service.live,
        channel=current_service.broadcast_channel,
        max_phones=broadcast_message.count_of_phones_likely,
    )

    if broadcast_message.status != 'pending-approval':
        return redirect(url_for(
            '.view_current_broadcast',
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        ))

    if current_service.trial_mode:
        broadcast_message.approve_broadcast()
        return redirect(url_for(
            '.broadcast_tour',
            service_id=current_service.id,
            step_index=6,
        ))
    elif form.validate_on_submit():
        broadcast_message.approve_broadcast()
    else:
        return render_template(
            'views/broadcast/view-message.html',
            broadcast_message=broadcast_message,
            back_link=url_for(
                _get_back_link_from_view_broadcast_endpoint(),
                service_id=current_service.id,
            ),
            form=form,
        )

    return redirect(url_for(
        '.view_current_broadcast',
        service_id=current_service.id,
        broadcast_message_id=broadcast_message.id,
    ))


@main.route('/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/reject')
@user_has_permissions('create_broadcasts', 'approve_broadcasts', restrict_admin_usage=True)
@service_has_permission('broadcast')
def reject_broadcast_message(service_id, broadcast_message_id):

    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    if broadcast_message.status != 'pending-approval':
        return redirect(url_for(
            '.view_current_broadcast',
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
@user_has_permissions('create_broadcasts', 'approve_broadcasts', restrict_admin_usage=False)
@service_has_permission('broadcast')
def cancel_broadcast_message(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    if broadcast_message.status != 'broadcasting':
        return redirect(url_for(
            '.view_current_broadcast',
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        ))

    if request.method == 'POST':
        broadcast_message.cancel_broadcast()
        return redirect(url_for(
            '.view_previous_broadcast',
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
