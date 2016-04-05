from flask import render_template
from flask_login import login_required

from app.main import main


headings = [
    'Trial mode',
    'Start with templates',
    'Add recipients',
    'Send your messages',
]


@main.route("/services/<service_id>/tour/<int:page>")
@login_required
def tour(service_id, page):
    return render_template(
        'views/tour/{}.html'.format(page),
        current_page=page,
        next_page=(page + 1),
        heading=headings[page - 1]
    )
