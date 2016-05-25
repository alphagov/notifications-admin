from datetime import datetime

import pytz
from flask import render_template
from flask_login import login_required

from app import statistics_api_client
from app.main import main
from app.utils import user_has_permissions
from app.statistics_utils import sum_of_statistics, add_rates_togi

@main.route("/platform-admin")
@login_required
@user_has_permissions(admin_override=True)
def platform_admin():
    return render_template(
        'views/platform-admin.html',
        global_stats=get_global_stats()
    )


def get_global_stats():
    day = datetime.now(tz=pytz.timezone('Europe/London')).date()
    all_stats = statistics_api_client.get_statistics_for_all_services_for_day(day)['data']
    return add_rates_to(sum_of_statistics(all_stats))
