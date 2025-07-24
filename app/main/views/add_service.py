from flask import current_app, redirect, render_template, request, session, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError

from app import service_api_client
from app.main import main
from app.main.forms import ChooseOrganisationForm, CreateNhsServiceForm, CreateServiceForm
from app.utils.user import user_is_gov_user, user_is_logged_in


def _create_service(service_name, organisation_type, form):
    try:
        service_id = service_api_client.create_service(
            service_name=service_name,
            organisation_type=organisation_type,
            email_message_limit=current_app.config["DEFAULT_SERVICE_LIMIT"],
            international_sms_message_limit=current_app.config["DEFAULT_SERVICE_INTERNATIONAL_SMS_LIMIT"],
            sms_message_limit=current_app.config["DEFAULT_SERVICE_LIMIT"],
            letter_message_limit=current_app.config["DEFAULT_SERVICE_LIMIT"],
            restricted=True,
            user_id=session["user_id"],
        )
        session["service_id"] = service_id

        return service_id, None
    except HTTPError as e:
        if e.status_code == 400:
            error_message = service_api_client.parse_edit_service_http_error(e)
            if not error_message:
                raise e

            form.name.errors.append(error_message)

            return None, e


def _create_example_template(service_id):
    example_sms_template = service_api_client.create_service_template(
        name="Example text message template",
        type_="sms",
        content="Hey ((name)), I’m trying out Notify. Today is ((day of week)) and my favourite colour is ((colour)).",
        service_id=service_id,
    )
    return example_sms_template


@main.route("/add-service/service-name", methods=["GET", "POST"])
@user_is_logged_in
@user_is_gov_user
def add_service_service_name():
    default_organisation_type = current_user.default_organisation_type
    if default_organisation_type == "nhs":
        form = CreateNhsServiceForm()
        default_organisation_type = None
    else:
        form = CreateServiceForm(organisation_type=default_organisation_type)

    if form.validate_on_submit():
        service_name = form.name.data

        service_id, error = _create_service(
            service_name,
            default_organisation_type or form.organisation_type.data,
            form,
        )
        if error:
            return _render_add_service_page(form, default_organisation_type)

        return redirect(url_for("main.add_service_test_mode"))

    else:
        return _render_add_service_page(form, default_organisation_type)


def _render_add_service_page(form, default_organisation_type):
    return render_template(
        "views/add-service.html",
        form=form,
        default_organisation_type=default_organisation_type,
        error_summary_enabled=True,
    )


@main.route("/add-service/choose-organisation", methods=["GET", "POST"])
@user_is_logged_in
@user_is_gov_user
def add_service_choose_organisation():
    default_org = current_user.default_organisation
    form = ChooseOrganisationForm(default_organisation=default_org.name)

    form.organisation.data = "default"

    if form.validate_on_submit():
        return redirect(url_for("main.add_service_service_name"))

    return render_template("views/add-service-choose-organisation.html", form=form)


@main.route("/add-service/test-mode", methods=["GET", "POST"])
@user_is_logged_in
@user_is_gov_user
def add_service_test_mode():
    service_id = session.get("service_id")

    if not service_id:
        return redirect(url_for("main.add_service_service_name"))

    if request.method == "POST":
        example_sms_template = _create_example_template(service_id)
        return redirect(
            url_for("main.begin_tour", service_id=service_id, template_id=example_sms_template["data"]["id"])
        )

    return render_template("views/add-service-test-mode.html")
