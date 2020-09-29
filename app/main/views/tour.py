from flask import abort, render_template

from app import current_service, current_user, url_for
from app.main import main
from app.utils import get_template, user_has_permissions


@main.route("/services/<uuid:service_id>/tour/<uuid:template_id>")
@user_has_permissions('send_messages')
def begin_tour(service_id, template_id):
    db_template = current_service.get_template(template_id)

    if (db_template['template_type'] != 'sms' or not current_user.mobile_number):
        abort(404)

    template = get_template(
        db_template,
        current_service,
        show_recipient=True,
    )

    template.values = {"phone_number": current_user.mobile_number}

    return render_template(
        'views/templates/start-tour.html',
        template=template,
        help='1',
        continue_link=url_for('.tour_step', service_id=service_id, template_id=template_id, step_index=1)
    )


@main.route(
    "/services/<uuid:service_id>/tour/<uuid:template_id>/step-<int:step_index>",
    methods=['GET', 'POST'],
)
@user_has_permissions('send_messages', restrict_admin_usage=True)
def tour_step(service_id, template_id, step_index):
    pass
