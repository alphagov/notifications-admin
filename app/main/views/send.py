import itertools
from string import ascii_uppercase
from zipfile import BadZipFile

from flask import (
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user
from notifications_python_client.errors import HTTPError
from notifications_utils import SMS_CHAR_COUNT_LIMIT
from notifications_utils.insensitive_dict import InsensitiveDict, InsensitiveSet
from notifications_utils.recipient_validation.postal_address import PostalAddress, address_lines_1_to_7_keys
from notifications_utils.recipients import RecipientCSV, first_column_headings
from notifications_utils.sanitise_text import SanitiseASCII
from xlrd.biffh import XLRDError
from xlrd.xldate import XLDateError

from app import (
    current_service,
    job_api_client,
    nl2br,
    notification_api_client,
    service_api_client,
    template_preview_client,
)
from app.main import main, no_cookie
from app.main.forms import (
    ChooseTimeForm,
    CsvUploadForm,
    LetterAddressForm,
    SetSenderForm,
    get_placeholder_form_instance,
)
from app.models.contact_list import ContactList, ContactListsAlphabetical
from app.models.user import Users
from app.s3_client.s3_csv_client import (
    get_csv_metadata,
    s3download,
    s3upload,
    set_metadata_on_csv_upload,
)
from app.utils import PermanentRedirect, should_skip_template_page, unicode_truncate
from app.utils.csv import Spreadsheet, get_errors_for_csv
from app.utils.user import user_has_permissions

letter_address_columns = [column.replace("_", " ") for column in address_lines_1_to_7_keys]


def get_example_csv_fields(column_headers, use_example_as_example, submitted_fields):
    if use_example_as_example:
        return ["example" for header in column_headers]
    elif submitted_fields:
        return [submitted_fields.get(header) for header in column_headers]
    else:
        return list(column_headers)


def get_example_csv_rows(template, use_example_as_example=True, submitted_fields=False):
    return {
        "email": ["test@example.com"] if use_example_as_example else [current_user.email_address],
        "sms": ["07700 900321"] if use_example_as_example else [current_user.mobile_number],
        "letter": [
            (submitted_fields or {}).get(key, get_example_letter_address(key) if use_example_as_example else key)
            for key in letter_address_columns
        ],
    }[template.template_type] + get_example_csv_fields(
        (
            placeholder
            for placeholder in template.placeholders
            if placeholder not in InsensitiveDict.from_keys(first_column_headings[template.template_type])
        ),
        use_example_as_example,
        submitted_fields,
    )


def get_example_letter_address(key):
    return {"address line 1": "A. Name", "address line 2": "123 Example Street", "address line 3": "XM4 5HQ"}.get(
        key, ""
    )


@main.route("/services/<uuid:service_id>/send/<uuid:template_id>/csv", methods=["GET", "POST"])
@user_has_permissions("send_messages")
def send_messages(service_id, template_id):
    template = current_service.get_template_with_user_permission_or_403(
        template_id,
        current_user,
        show_recipient=True,
        letter_preview_url=url_for(
            "no_cookie.view_letter_template_preview",
            service_id=service_id,
            template_id=template_id,
            filetype="png",
        ),
    )

    if template.template_type == "email":
        template.reply_to = get_email_reply_to_address_from_session()
    elif template.template_type == "sms":
        template.sender = get_sms_sender_from_session()
        template.show_sender = bool(template.sender)

    if template.template_type not in current_service.available_template_types:
        return redirect(
            url_for(
                ".action_blocked",
                service_id=service_id,
                notification_type=template.template_type,
                return_to="view_template",
                template_id=template_id,
            )
        )

    form = CsvUploadForm()
    if form.validate_on_submit():
        try:
            current_app.logger.info(
                "User %(user_id)s uploaded %(filename)s",
                {"user_id": current_user.id, "filename": form.file.data.filename},
            )
            upload_id = s3upload(service_id, Spreadsheet.from_file_form(form).as_dict, current_app.config["AWS_REGION"])
            current_app.logger.info(
                "%(filename)s persisted in S3 as %(upload_id)s",
                {"filename": form.file.data.filename, "upload_id": upload_id},
            )
            file_name_metadata = unicode_truncate(SanitiseASCII.encode(form.file.data.filename), 1600)
            set_metadata_on_csv_upload(service_id, upload_id, original_file_name=file_name_metadata)
            return redirect(
                url_for(
                    ".check_messages",
                    service_id=service_id,
                    upload_id=upload_id,
                    template_id=template.id,
                )
            )
        except (UnicodeDecodeError, BadZipFile, XLRDError):
            current_app.logger.warning("Could not read %s", form.file.data.filename, exc_info=True)
            form.file.errors = ["Notify cannot read this file - try using a different file type"]
        except XLDateError:
            current_app.logger.warning("Could not parse numbers/dates in %s", form.file.data.filename, exc_info=True)
            form.file.errors = ["Notify cannot read this file - try saving it as a CSV instead"]
    elif form.errors:
        # just show the first error, as we don't expect the form to have more
        # than one, since it only has one field
        first_field_errors = list(form.errors.values())[0]
        form.file.errors.append(first_field_errors[0])

    column_headings = get_spreadsheet_column_headings_from_template(template)

    return render_template(
        "views/send.html",
        template=template,
        column_headings=list(ascii_uppercase[: len(column_headings)]),
        example=[column_headings, get_example_csv_rows(template)],
        form=form,
        allowed_file_extensions=Spreadsheet.ALLOWED_FILE_EXTENSIONS,
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/send/<uuid:template_id>.csv", methods=["GET"])
@user_has_permissions("send_messages", "manage_templates")
def get_example_csv(service_id, template_id):
    template = current_service.get_template(template_id)
    return (
        Spreadsheet.from_rows(
            [get_spreadsheet_column_headings_from_template(template), get_example_csv_rows(template)]
        ).as_csv_data,
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f'inline; filename="{template.name}.csv"',
        },
    )


def _should_show_set_sender_page(service_id, template) -> bool:
    if template.template_type == "letter":
        return False

    sender_details = get_sender_details(service_id, template.template_type)

    if len(sender_details) <= 1:
        return False

    return True


@main.route("/services/<uuid:service_id>/send/<uuid:template_id>/set-sender", methods=["GET", "POST"])
@user_has_permissions("send_messages")
def set_sender(service_id, template_id):
    from_back_link = request.args.get("from_back_link") == "yes"
    # If we're returning to the page, we want to use the sender_id already in the session instead of resetting it
    session["sender_id"] = session.get("sender_id") if from_back_link else None

    redirect_to_one_off = redirect(url_for(".send_one_off", service_id=service_id, template_id=template_id))

    template = current_service.get_template_with_user_permission_or_403(template_id, current_user)

    if template.template_type == "letter":
        return redirect_to_one_off

    sender_details = get_sender_details(service_id, template.template_type)

    if len(sender_details) == 1:
        session["sender_id"] = sender_details[0]["id"]

    if len(sender_details) <= 1:
        return redirect_to_one_off

    sender_context = get_sender_context(sender_details, template.template_type)

    selected_sender = session["sender_id"] or sender_context["default_id"]

    form = SetSenderForm(
        sender=selected_sender,
        sender_choices=sender_context["value_and_label"],
        sender_label=sender_context["description"],
    )
    option_hints = {sender_context["default_id"]: "(Default)"}
    if sender_context.get("receives_text_message", None):
        option_hints.update({sender_context["receives_text_message"]: "(Receives replies)"})
    if sender_context.get("default_and_receives", None):
        option_hints = {sender_context["default_and_receives"]: "(Default and receives replies)"}

    # extend all radios that need hint text
    form.sender.param_extensions = {"items": []}
    for item_id, _item_value in form.sender.choices:
        if item_id in option_hints:
            extensions = {"hint": {"text": option_hints[item_id]}}
        else:
            extensions = {}  # if no extensions needed, send an empty dict to preserve order of items
        form.sender.param_extensions["items"].append(extensions)

    if form.validate_on_submit():
        session["sender_id"] = form.sender.data
        return redirect(url_for(".send_one_off", service_id=service_id, template_id=template_id))

    return render_template(
        "views/templates/set-sender.html",
        form=form,
        template_id=template_id,
        sender_context={"title": sender_context["title"], "description": sender_context["description"]},
        option_hints=option_hints,
        back_link=_get_set_sender_back_link(service_id, template),
    )


def get_sender_context(sender_details, template_type):
    context = {
        "email": {
            "title": "Where should replies come back to?",
            "description": "Where should replies come back to?",
            "field_name": "email_address",
        },
        "letter": {
            "title": "Send to one recipient",
            "description": "What should appear in the top right of the letter?",
            "field_name": "contact_block",
        },
        "sms": {
            "title": "Who should the message come from?",
            "description": "Who should the message come from?",
            "field_name": "sms_sender",
        },
    }[template_type]

    sender_format = context["field_name"]

    context["default_id"] = next(sender["id"] for sender in sender_details if sender["is_default"])
    if template_type == "sms":
        inbound = [sender["id"] for sender in sender_details if sender["inbound_number_id"]]
        if inbound:
            context["receives_text_message"] = next(iter(inbound))
        if context["default_id"] == context.get("receives_text_message", None):
            context["default_and_receives"] = context["default_id"]

    context["value_and_label"] = [(sender["id"], nl2br(sender[sender_format])) for sender in sender_details]
    return context


def get_sender_details(service_id, template_type):
    api_call = {
        "email": service_api_client.get_reply_to_email_addresses,
        "letter": service_api_client.get_letter_contacts,
        "sms": service_api_client.get_sms_senders,
    }[template_type]
    return api_call(service_id)


@main.route("/services/<uuid:service_id>/send/<uuid:template_id>/one-off")
@user_has_permissions("send_messages")
def send_one_off(service_id, template_id):
    session["recipient"] = None
    session["placeholders"] = {}

    template = current_service.get_template_with_user_permission_or_403(template_id, current_user)
    if template.template_type == "letter":
        session["sender_id"] = None
        return redirect(url_for(".send_one_off_letter_address", service_id=service_id, template_id=template_id))

    if template.template_type not in current_service.available_template_types:
        return redirect(
            url_for(
                ".action_blocked",
                service_id=service_id,
                notification_type=template.template_type,
                return_to="view_template",
                template_id=template_id,
            )
        )

    return redirect(
        url_for(
            ".send_one_off_step",
            service_id=service_id,
            template_id=template_id,
            step_index=0,
        )
    )


def get_notification_check_endpoint(service_id, template):
    return redirect(
        url_for(
            "main.check_notification",
            service_id=service_id,
            template_id=template.id,
        )
    )


@main.route("/services/<uuid:service_id>/send/<uuid:template_id>/one-off/address", methods=["GET", "POST"])
@user_has_permissions("send_messages")
def send_one_off_letter_address(service_id, template_id):
    if {"recipient", "placeholders"} - set(session.keys()):
        # if someone has come here via a bookmark or back button they might have some stuff still in their session
        return redirect(url_for(".send_one_off", service_id=service_id, template_id=template_id))

    template = current_service.get_template_with_user_permission_or_403(
        template_id,
        current_user,
        show_recipient=True,
        letter_preview_url=url_for(
            "no_cookie.send_test_preview",
            service_id=service_id,
            template_id=template_id,
            filetype="png",
        ),
    )

    session_placeholders = get_normalised_placeholders_from_session()

    current_session_address = PostalAddress.from_personalisation(session_placeholders)

    form = LetterAddressForm(
        address=current_session_address.normalised,
        allow_international_letters=current_service.has_permission("international_letters"),
    )

    if form.validate_on_submit():
        session["placeholders"].update(PostalAddress(form.address.data).as_personalisation)

        placeholders = fields_to_fill_in(template)
        if all_placeholders_in_session(placeholders):
            return get_notification_check_endpoint(service_id, template)

        first_non_address_placeholder_index = len(address_lines_1_to_7_keys)

        return redirect(
            url_for(
                "main.send_one_off_step",
                service_id=service_id,
                template_id=template_id,
                step_index=first_non_address_placeholder_index,
            )
        )

    return render_template(
        "views/send-one-off-letter-address.html",
        page_title=get_send_test_page_title(
            template_type="letter",
            entering_recipient=True,
            name=template.name,
        ),
        template=template,
        form=form,
        back_link=get_back_link(service_id, template, 0),
        link_to_upload=True,
        error_summary_enabled=True,
    )


@main.route(
    "/services/<uuid:service_id>/send/<uuid:template_id>/one-off/step-<int:step_index>",
    methods=["GET", "POST"],
)
@user_has_permissions("send_messages")
def send_one_off_step(service_id, template_id, step_index):  # noqa: C901
    if {"recipient", "placeholders"} - set(session.keys()):
        return redirect(
            url_for(
                ".send_one_off",
                service_id=service_id,
                template_id=template_id,
            )
        )

    # Clear the session variable which indicates we've come from the inbound SMS flow if step_index is 0.
    # If step_index is 0, the message was not sent from the inbound SMS flow, which starts at step_index 1.
    if step_index == 0:
        session.pop("from_inbound_sms_details", None)

    template = current_service.get_template_with_user_permission_or_403(
        template_id,
        current_user,
        show_recipient=True,
        letter_preview_url=url_for(
            "no_cookie.send_test_preview",
            service_id=service_id,
            template_id=template_id,
            filetype="png",
        ),
    )

    if template.template_type == "email":
        template.reply_to = get_email_reply_to_address_from_session()
    elif template.template_type == "sms":
        template.sender = get_sms_sender_from_session()
        template.show_sender = bool(template.sender)

    template_values = get_recipient_and_placeholders_from_session(template.template_type)

    placeholders = fields_to_fill_in(template)

    try:
        current_placeholder = placeholders[step_index]
    except IndexError:
        if all_placeholders_in_session(placeholders):
            return get_notification_check_endpoint(service_id, template)
        return redirect(
            url_for(
                ".send_one_off",
                service_id=service_id,
                template_id=template_id,
            )
        )

    # if we're in a letter, we should show address block rather than "address line #" or "postcode"
    if template.template_type == "letter":
        if step_index < len(address_lines_1_to_7_keys):
            return redirect(
                url_for(
                    ".send_one_off_letter_address",
                    service_id=service_id,
                    template_id=template_id,
                )
            )
        if current_placeholder in InsensitiveDict(PostalAddress("").as_personalisation):
            return redirect(
                url_for(
                    request.endpoint,
                    service_id=service_id,
                    template_id=template_id,
                    step_index=step_index + 1,
                )
            )
    form = get_placeholder_form_instance(
        current_placeholder,
        dict_to_populate_from=get_normalised_placeholders_from_session(),
        template_type=template.template_type,
        allow_international_phone_numbers=current_service.has_permission("international_sms"),
        allow_sms_to_uk_landline=current_service.has_permission("sms_to_uk_landlines"),
    )

    template.values = template_values

    if form.validate_on_submit():
        # if it's the first input (phone/email), we store against `recipient` as well, for easier extraction.
        # Only if it's not a letter.
        # And only if we're not on the test route, since that will already have the user's own number set
        if step_index == 0 and template.template_type != "letter":
            session["recipient"] = form.placeholder_value.data

        session["placeholders"][current_placeholder] = form.placeholder_value.data

        template.values[current_placeholder] = form.placeholder_value.data
        if template.template_type == "letter" and template.has_qr_code_with_too_much_data():
            form.placeholder_value.errors.append(
                "Cannot create a usable QR code - the text you entered makes the link too long"
            )

        else:
            if all_placeholders_in_session(placeholders):
                return get_notification_check_endpoint(service_id, template)

            return redirect(
                url_for(
                    request.endpoint,
                    service_id=service_id,
                    template_id=template_id,
                    step_index=step_index + 1,
                )
            )

    back_link = get_back_link(service_id, template, step_index, placeholders)
    template.values[current_placeholder] = None

    return render_template(
        "views/send-test.html",
        page_title=get_send_test_page_title(
            template.template_type,
            entering_recipient=not session["recipient"],
            name=template.name,
        ),
        template=template,
        form=form,
        skip_link=get_skip_link(step_index, template),
        back_link=back_link,
        link_to_upload=(request.endpoint == "main.send_one_off_step" and step_index == 0),
        error_summary_enabled=True,
    )


@no_cookie.route(
    "/services/<uuid:service_id>/send/<uuid:template_id>/test.<letter_file_extension:filetype>", methods=["GET"]
)
@user_has_permissions("send_messages")
def send_test_preview(service_id, template_id, filetype):
    template = current_service.get_template_with_user_permission_or_403(
        template_id,
        current_user,
        letter_preview_url=url_for(
            "no_cookie.send_test_preview",
            service_id=service_id,
            template_id=template_id,
            filetype="png",
        ),
    )

    return template_preview_client.get_preview_for_templated_letter(
        db_template=template._template,
        filetype=filetype,
        values=get_normalised_placeholders_from_session(),
        page=request.args.get("page"),
        service=current_service,
    )


@main.route("/services/<uuid:service_id>/send/<uuid:template_id>/from-contact-list")
@user_has_permissions("send_messages")
def choose_from_contact_list(service_id, template_id):
    template = current_service.get_template_with_user_permission_or_403(template_id, current_user)
    return render_template(
        "views/send-contact-list.html",
        contact_lists=ContactListsAlphabetical(
            current_service.id,
            template_type=template.template_type,
        ),
        template=template,
    )


@main.route("/services/<uuid:service_id>/send/<uuid:template_id>/from-contact-list/<uuid:contact_list_id>")
@user_has_permissions("send_messages")
def send_from_contact_list(service_id, template_id, contact_list_id):
    contact_list = ContactList.from_id(
        contact_list_id,
        service_id=current_service.id,
    )
    return redirect(
        url_for(
            "main.check_messages",
            service_id=current_service.id,
            template_id=template_id,
            upload_id=contact_list.copy_to_uploads(),
            contact_list_id=contact_list.id,
            emergency_contact=True,
        )
    )


def _check_messages(service_id, template_id, upload_id, preview_row, emergency_contact=False):
    try:
        # The happy path is that the job doesn’t already exist, so the
        # API will return a 404 and the client will raise HTTPError.
        job_api_client.get_job(service_id, upload_id)

        # the job exists already - so go back to the templates page
        # If we just return a `redirect` (302) object here, we'll get
        # errors when we try and unpack in the check_messages route.
        # Rasing a werkzeug.routing redirect means that doesn't happen.
        raise PermanentRedirect(url_for("main.send_messages", service_id=service_id, template_id=template_id))
    except HTTPError as e:
        if e.status_code != 404:
            raise
    contents = s3download(service_id, upload_id)

    template = current_service.get_template_with_user_permission_or_403(
        template_id,
        current_user,
        show_recipient=True,
        letter_preview_url=url_for(
            "no_cookie.check_messages_preview",
            service_id=service_id,
            template_id=template_id,
            upload_id=upload_id,
            filetype="png",
            row_index=preview_row,
        ),
    )

    remaining_messages = current_service.remaining_messages(template.template_type)
    remaining_international_sms_messages = current_service.remaining_messages("international_sms")

    if template.template_type == "email":
        template.reply_to = get_email_reply_to_address_from_session()
    elif template.template_type == "sms":
        template.sender = get_sms_sender_from_session()
        template.show_sender = bool(template.sender)
    recipients = RecipientCSV(
        contents,
        template=template,
        max_initial_rows_shown=50,
        max_errors_shown=50,
        guestlist=(
            itertools.chain.from_iterable(
                [user.name, user.mobile_number, user.email_address] for user in Users(service_id)
            )
            if current_service.trial_mode
            else None
        ),
        remaining_messages=remaining_messages,
        remaining_international_sms_messages=remaining_international_sms_messages,
        allow_international_sms=current_service.has_permission("international_sms"),
        allow_sms_to_uk_landline=current_service.has_permission("sms_to_uk_landlines"),
        allow_international_letters=current_service.has_permission("international_letters"),
        should_validate_phone_number=not emergency_contact,
    )
    if request.args.get("from_test"):
        # only happens if generating a letter preview test
        back_link = url_for("main.send_one_off", service_id=service_id, template_id=template.id)
        choose_time_form = None
    else:
        back_link = url_for("main.send_messages", service_id=service_id, template_id=template.id)
        choose_time_form = ChooseTimeForm()

    if preview_row < 2:
        abort(404)

    if preview_row < len(recipients) + 2:
        template.values = recipients[preview_row - 2].recipient_and_personalisation
    elif preview_row > 2:
        abort(404)
    original_file_name = get_csv_metadata(service_id, upload_id).get("original_file_name", "")
    return {
        "recipients": recipients,
        "template": template,
        "errors": recipients.has_errors,
        "row_errors": get_errors_for_csv(recipients, template.template_type),
        "count_of_recipients": len(recipients),
        "count_of_displayed_recipients": len(list(recipients.displayed_rows)),
        "original_file_name": original_file_name,
        "upload_id": upload_id,
        "form": CsvUploadForm(),
        "remaining_messages": remaining_messages,
        "remaining_international_sms_messages": remaining_international_sms_messages,
        "_choose_time_form": choose_time_form,
        "back_link": back_link,
        "trying_to_send_letters_in_trial_mode": all(
            (
                current_service.trial_mode,
                template.template_type == "letter",
            )
        ),
        "first_recipient_column": recipients.recipient_column_headers[0],
        "preview_row": preview_row,
        "sent_previously": job_api_client.has_sent_previously(
            service_id, template.id, template.get_raw("version"), original_file_name
        ),
        "letter_min_address_lines": PostalAddress.MIN_LINES,
        "letter_max_address_lines": PostalAddress.MAX_LINES,
    }


@main.route("/services/<uuid:service_id>/<uuid:template_id>/check/<uuid:upload_id>", methods=["GET"])
@main.route(
    "/services/<uuid:service_id>/<uuid:template_id>/check/<uuid:upload_id>/row-<int:row_index>", methods=["GET"]
)
@user_has_permissions("send_messages")
def check_messages(service_id, template_id, upload_id, row_index=2):
    emergency_contact = bool(request.args.get("emergency_contact"))
    data = _check_messages(service_id, template_id, upload_id, row_index, emergency_contact)
    data["allowed_file_extensions"] = Spreadsheet.ALLOWED_FILE_EXTENSIONS
    if (
        data["recipients"].too_many_rows
        or not data["count_of_recipients"]
        or not data["recipients"].has_recipient_columns
        or data["recipients"].duplicate_recipient_column_headers
        or data["recipients"].missing_column_headers
        or data["sent_previously"]
    ):
        return render_template("views/check/column-errors.html", **data)

    if data["row_errors"]:
        return render_template("views/check/row-errors.html", **data)

    if data["errors"] or data["trying_to_send_letters_in_trial_mode"]:
        return render_template("views/check/column-errors.html", **data)

    metadata_kwargs = {
        "notification_count": data["count_of_recipients"],
        "template_id": template_id,
        "valid": True,
        "original_file_name": data.get("original_file_name", ""),
    }

    if session.get("sender_id") and data["template"].template_type != "letter":
        # sender_id is not an option for sending letters.
        metadata_kwargs["sender_id"] = session["sender_id"]

    set_metadata_on_csv_upload(service_id, upload_id, **metadata_kwargs)

    return render_template("views/check/ok.html", **data)


@no_cookie.route(
    "/services/<uuid:service_id>/<uuid:template_id>/check/<uuid:upload_id>.<letter_file_extension:filetype>",
    methods=["GET"],
)
@no_cookie.route(
    "/services/<uuid:service_id>/<uuid:template_id>/check/<uuid:upload_id>/row-<int:row_index>.<letter_file_extension:filetype>",
    methods=["GET"],
)
@user_has_permissions("send_messages")
def check_messages_preview(service_id, template_id, upload_id, filetype, row_index=2):
    if filetype == "pdf":
        page = None
    if filetype == "png":
        page = request.args.get("page", 1)

    template = _check_messages(service_id, template_id, upload_id, row_index)["template"]
    return template_preview_client.get_preview_for_templated_letter(
        db_template=template._template,
        filetype=filetype,
        values=template.values,
        page=page,
        service=current_service,
    )


@no_cookie.route(
    "/services/<uuid:service_id>/<uuid:template_id>/check.<letter_file_extension:filetype>",
    methods=["GET"],
)
@user_has_permissions("send_messages")
def check_notification_preview(service_id, template_id, filetype):
    if filetype == "pdf":
        page = None
    if filetype == "png":
        page = request.args.get("page", 1)

    template = _check_notification(
        service_id,
        template_id,
    )["template"]
    return template_preview_client.get_preview_for_templated_letter(
        db_template=template._template,
        filetype=filetype,
        values=template.values,
        page=page,
        service=current_service,
    )


@main.route("/services/<uuid:service_id>/start-job/<uuid:upload_id>", methods=["POST"])
@user_has_permissions("send_messages", restrict_admin_usage=True)
def start_job(service_id, upload_id):
    job_api_client.create_job(
        upload_id,
        service_id,
        scheduled_for=request.form.get("scheduled_for", ""),
        contact_list_id=request.form.get("contact_list_id", ""),
    )

    session.pop("sender_id", None)

    return redirect(
        url_for(
            "main.view_job",
            job_id=upload_id,
            service_id=service_id,
            just_sent="yes",
        )
    )


def fields_to_fill_in(template, prefill_current_user=False):
    if "letter" == template.template_type:
        return InsensitiveSet(letter_address_columns + list(template.placeholders))

    if not prefill_current_user:
        return InsensitiveSet(first_column_headings[template.template_type] + list(template.placeholders))

    if template.template_type == "sms":
        session["recipient"] = current_user.mobile_number
        session["placeholders"]["phone number"] = current_user.mobile_number
    else:
        session["recipient"] = current_user.email_address
        session["placeholders"]["email address"] = current_user.email_address

    return InsensitiveSet(template.placeholders)


def get_normalised_placeholders_from_session():
    return InsensitiveDict(session.get("placeholders", {}))


def get_recipient_and_placeholders_from_session(template_type):
    placeholders = get_normalised_placeholders_from_session()

    if template_type == "sms":
        placeholders["phone_number"] = session["recipient"]
    else:
        placeholders["email_address"] = session["recipient"]

    return placeholders


def all_placeholders_in_session(placeholders):
    return all(
        get_normalised_placeholders_from_session().get(placeholder, False) not in (False, None)
        for placeholder in placeholders
    )


def get_send_test_page_title(template_type, entering_recipient, name=None):
    if entering_recipient:
        return f"Send ‘{name}’"
    return "Personalise this message"


def _get_set_sender_back_link(service_id, template):
    if should_skip_template_page(template):
        return url_for(
            ".choose_template",
            service_id=service_id,
        )
    else:
        return url_for(
            "main.view_template",
            service_id=service_id,
            template_id=template.id,
        )


def get_back_link(service_id, template, step_index, placeholders=None):
    if step_index == 0:
        if _should_show_set_sender_page(service_id, template):
            return url_for("main.set_sender", service_id=service_id, template_id=template.id, from_back_link="yes")
        else:
            return _get_set_sender_back_link(service_id, template)

    if step_index == 1 and template.template_type == "sms" and "from_inbound_sms_details" in session:
        notification_id = session["from_inbound_sms_details"]["notification_id"]
        from_folder = session["from_inbound_sms_details"]["from_folder"]

        if from_folder:
            return url_for(
                "main.conversation_reply",
                service_id=service_id,
                notification_id=notification_id,
                from_folder=from_folder,
            )
        else:
            return url_for("main.conversation_reply", service_id=service_id, notification_id=notification_id)

    if template.template_type == "letter" and placeholders:
        # Make sure we’re not redirecting users to a page which will
        # just redirect them forwards again
        back_link_destination_step_index = next(
            (
                index
                for index, placeholder in reversed(list(enumerate(placeholders[:step_index])))
                if placeholder not in InsensitiveDict(PostalAddress("").as_personalisation)
            ),
            1,
        )
        return get_back_link(service_id, template, back_link_destination_step_index + 1)

    return url_for(
        "main.send_one_off_step",
        service_id=service_id,
        template_id=template.id,
        step_index=step_index - 1,
    )


def get_skip_link(step_index, template):
    if (
        request.endpoint == "main.send_one_off_step"
        and step_index == 0
        and template.template_type in ("sms", "email")
        and not (template.template_type == "sms" and current_user.mobile_number is None)
        and current_user.has_permissions("manage_templates", "manage_service")
    ):
        return (
            f"Use my {first_column_headings[template.template_type][0]}",
            url_for(".send_one_off_to_myself", service_id=current_service.id, template_id=template.id),
        )


@main.route("/services/<uuid:service_id>/template/<uuid:template_id>/one-off/send-to-myself", methods=["GET"])
@user_has_permissions("send_messages")
def send_one_off_to_myself(service_id, template_id):
    # We aren't concerned with creating the exact template (for example adding recipient and sender names)
    # we just want to create enough to use `fields_to_fill_in`
    template = current_service.get_template_with_user_permission_or_403(template_id, current_user)

    if template.template_type not in ("sms", "email"):
        abort(404)

    fields_to_fill_in(template, prefill_current_user=True)

    return redirect(
        url_for(
            "main.send_one_off_step",
            service_id=service_id,
            template_id=template_id,
            step_index=1,
        )
    )


@main.route("/services/<uuid:service_id>/template/<uuid:template_id>/notification/check", methods=["GET"])
@user_has_permissions("send_messages")
def check_notification(service_id, template_id):
    return render_template(
        "views/notifications/check.html",
        **_check_notification(service_id, template_id),
    )


def _check_notification(service_id, template_id, exception=None):
    template = current_service.get_template_with_user_permission_or_403(
        template_id,
        current_user,
        show_recipient=True,
        letter_preview_url=url_for(
            "no_cookie.check_notification_preview",
            service_id=service_id,
            template_id=template_id,
            filetype="png",
        ),
    )
    if template.template_type == "email":
        template.reply_to = get_email_reply_to_address_from_session()
    elif template.template_type == "sms":
        template.sender = get_sms_sender_from_session()
        template.show_sender = bool(template.sender)

    placeholders = fields_to_fill_in(template)

    back_link = get_back_link(service_id, template, len(placeholders), placeholders)

    if (not session.get("recipient") and template.template_type != "letter") or not all_placeholders_in_session(
        template.placeholders
    ):
        raise PermanentRedirect(back_link)

    template.values = get_recipient_and_placeholders_from_session(template.template_type)

    return dict(
        template=template,
        back_link=back_link,
        **(get_template_error_dict(exception) if exception else {}),
    )


def get_template_error_dict(exception):
    # TODO: Make API return some computer-friendly identifier as well as the end user error messages
    if "service is in trial mode" in exception.message:
        error = "not-allowed-to-send-to"
    elif "Exceeded send limits" in exception.message:
        if "international_sms" in exception.message:
            error = "too-many-international-sms-messages"
        else:
            error = "too-many-messages"
    # the error from the api is changing for message-too-long, but we need both until the api is deployed.
    elif "Content for template has a character count greater than the limit of" in exception.message:
        error = "message-too-long"
    elif "Text messages cannot be longer than" in exception.message:
        error = "message-too-long"
    else:
        raise exception

    return {
        "error": error,
        "SMS_CHAR_COUNT_LIMIT": SMS_CHAR_COUNT_LIMIT,
        "current_service": current_service,
        # used to trigger CSV specific err msg content, so not needed for single notification errors.
        "original_file_name": False,
    }


@main.route("/services/<uuid:service_id>/template/<uuid:template_id>/notification/check", methods=["POST"])
@user_has_permissions("send_messages", restrict_admin_usage=True)
def send_notification(service_id, template_id):
    recipient = get_recipient()

    if not recipient:
        return redirect(
            url_for(
                ".send_one_off",
                service_id=service_id,
                template_id=template_id,
            )
        )

    current_service.get_template_with_user_permission_or_403(template_id, current_user)

    try:
        noti = notification_api_client.send_notification(
            service_id,
            template_id=template_id,
            recipient=recipient,
            personalisation=session["placeholders"],
            sender_id=session.get("sender_id", None),
        )
    except HTTPError as exception:
        current_app.logger.info(
            'Service %(service_id)s could not send notification: "%(message)s"',
            {"service_id": current_service.id, "message": exception.message},
        )
        return render_template(
            "views/notifications/check.html",
            **_check_notification(service_id, template_id, exception),
        )

    session.pop("placeholders")
    session.pop("recipient")
    session.pop("sender_id", None)
    session.pop("from_inbound_sms_details", None)

    return redirect(
        url_for(
            "main.view_notification",
            service_id=service_id,
            notification_id=noti["id"],
            # used to show the final step of the tour (help=3) or not show
            # a back link on a just sent one off notification (help=0)
            help=request.args.get("help"),
        )
    )


def get_email_reply_to_address_from_session():
    if session.get("sender_id"):
        return current_service.get_email_reply_to_address(session["sender_id"])["email_address"]


def get_sms_sender_from_session():
    if session.get("sender_id"):
        return current_service.get_sms_sender(session["sender_id"])["sms_sender"]


def get_spreadsheet_column_headings_from_template(template):
    column_headings = []

    if template.template_type == "letter":
        # We want to avoid showing `address line 7` for now
        recipient_columns = letter_address_columns
    else:
        recipient_columns = first_column_headings[template.template_type]

    for column_heading in recipient_columns + list(template.placeholders):
        if column_heading not in InsensitiveDict.from_keys(column_headings):
            column_headings.append(column_heading)

    return column_headings


def get_recipient():
    if {"recipient", "placeholders"} - set(session.keys()):
        return None

    return (
        session["recipient"] or PostalAddress.from_personalisation(InsensitiveDict(session["placeholders"])).normalised
    )
