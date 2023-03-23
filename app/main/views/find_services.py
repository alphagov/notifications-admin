import uuid
from contextlib import suppress

from flask import redirect, render_template, request, url_for

from app import service_api_client
from app.main import main
from app.main.forms import SearchByNameForm
from app.utils.user import user_is_platform_admin


@main.route("/find-services-by-name", methods=["GET"])
@user_is_platform_admin
def find_services_by_name():
    # The prefix on this form must match the prefix on the form on the platform_admin_find view as the form on that page
    # comes here with pre-populated search terms.
    form = SearchByNameForm(request.args, prefix="services", meta={"csrf": False})
    services_found = None
    if form.search.data is not None and form.validate():
        with suppress(ValueError):
            return redirect(url_for("main.service_dashboard", service_id=uuid.UUID(form.search.data)))
        services_found = service_api_client.find_services_by_name(service_name=form.search.data)["data"]
    return render_template("views/find-services/find-services-by-name.html", form=form, services_found=services_found)
