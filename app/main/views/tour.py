from flask import render_template
from flask_login import login_required

from app.main import main


@main.route("/services/<service_id>/tour/<int:page>")
@login_required
def tour(service_id, page):
    return render_template(
        'views/tour/{}.html'.format(page),
        service_id=service_id,  # TODO: fix when Nick’s PR is merged
        current_page=page,
        next_page=(page + 1)
    )
