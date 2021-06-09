import uuid
from contextlib import suppress

from flask import redirect, render_template, url_for

from app import service_api_client
from app.main import main
from app.main.forms import SearchByNameForm
from app.utils.user import user_is_platform_admin


@main.route("/find-services-by-name", methods=['GET', 'POST'])
@user_is_platform_admin
def find_services_by_name():
    form = SearchByNameForm()
    services_found = None
    if form.validate_on_submit():
        with suppress(ValueError):
            return redirect(url_for(
                'main.service_dashboard',
                service_id=uuid.UUID(form.search.data)
            ))
        services_found = service_api_client.find_services_by_name(service_name=form.search.data)['data']
    return render_template(
        'views/find-services/find-services-by-name.html',
        form=form,
        services_found=services_found
    )
