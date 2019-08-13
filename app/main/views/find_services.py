from flask import render_template, request

from app import service_api_client
from app.main import main
from app.main.forms import SearchByNameForm
from app.utils import user_is_platform_admin


@main.route("/find-services-by-name", methods=['GET', 'POST'])
@user_is_platform_admin
def find_services_by_name():
    form = SearchByNameForm()
    services_found = None
    status = 200
    if form.validate_on_submit():
        services_found = service_api_client.find_services_by_name(service_name=form.search.data)['data']
    elif request.method == 'POST':
        status = 400
    return render_template(
        'views/find-services/find-services-by-name.html',
        form=form,
        services_found=services_found
    ), status
