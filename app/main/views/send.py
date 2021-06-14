import itertools
from string import ascii_uppercase
from zipfile import BadZipFile

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user
from notifications_python_client.errors import HTTPError
from notifications_utils import LETTER_MAX_PAGE_COUNT, SMS_CHAR_COUNT_LIMIT
from notifications_utils.columns import Columns
from notifications_utils.pdf import is_letter_too_long
from notifications_utils.postal_address import (
    PostalAddress,
    address_lines_1_to_7_keys,
)
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
from app.template_previews import TemplatePreview, get_page_count_for_letter
from app.utils import (
    PermanentRedirect,
    should_skip_template_page,
    unicode_truncate,
)
from app.utils.csv import Spreadsheet, get_errors_for_csv
from app.utils.templates import get_template
from app.utils.user import user_has_permissions

letter_address_columns = [
    column.replace('_', ' ')
    for column in address_lines_1_to_7_keys
]


def get_example_csv_fields(column_headers, use_example_as_example, submitted_fields):
    if use_example_as_example:
        return ["example" for header in column_headers]
    elif submitted_fields:
        return [submitted_fields.get(header) for header in column_headers]
    else:
        return list(column_headers)


def get_example_csv_rows(template, use_example_as_example=True, submitted_fields=False):
    return {
        'email': ['test@example.com'] if use_example_as_example else [current_user.email_address],
        'sms': ['07700 900321'] if use_example_as_example else [current_user.mobile_number],
        'letter': [
            (submitted_fields or {}).get(
                key, get_example_letter_address(key) if use_example_as_example else key
            )
            for key in letter_address_columns
        ]
    }[template.template_type] + get_example_csv_fields(
        (
            placeholder for placeholder in template.placeholders
            if placeholder not in Columns.from_keys(
                first_column_headings[template.template_type]
            )
        ),
        use_example_as_example,
        submitted_fields
    )


def get_example_letter_address(key):
    return {
        'address line 1': 'A. Name',
        'address line 2': '123 Example Street',
        'address line 3': 'XM4 5HQ'
    }.get(key, '')


@main.route("/services/<uuid:service_id>/send/<uuid:template_id>/csv", methods=['GET', 'POST'])
@user_has_permissions('send_messages', restrict_admin_usage=True)
def send_messages(service_id, template_id):
    db_template = current_service.get_template_with_user_permission_or_403(template_id, current_user)

    email_reply_to = None
    sms_sender = None

    if db_template['template_type'] == 'email':
        email_reply_to = get_email_reply_to_address_from_session()
    elif db_template['template_type'] == 'sms':
        sms_sender = get_sms_sender_from_session()

    if db_template['template_type'] not in current_service.available_template_types:
        return redirect(url_for(
            '.action_blocked',
            service_id=service_id,
            notification_type=db_template['template_type'],
            return_to='view_template',
            template_id=template_id
        ))

    template = get_template(
        db_template,
        current_service,
        show_recipient=True,
        letter_preview_url=url_for(
            'no_cookie.view_letter_template_preview',
            service_id=service_id,
            template_id=template_id,
            filetype='png',
            page_count=get_page_count_for_letter(db_template),
        ),
        email_reply_to=email_reply_to,
        sms_sender=sms_sender,
    )

    form = CsvUploadForm()
    if form.validate_on_submit():
        try:
            upload_id = s3upload(
                service_id,
                Spreadsheet.from_file_form(form).as_dict,
                current_app.config['AWS_REGION']
            )
            file_name_metadata = unicode_truncate(
                SanitiseASCII.encode(form.file.data.filename),
                1600
            )
            set_metadata_on_csv_upload(
                service_id,
                upload_id,
                original_file_name=file_name_metadata
            )
            return redirect(url_for(
                '.check_messages',
                service_id=service_id,
                upload_id=upload_id,
                template_id=template.id,
            ))
        except (UnicodeDecodeError, BadZipFile, XLRDError):
            flash('Could not read {}. Try using a different file format.'.format(
                form.file.data.filename
            ))
        except (XLDateError):
            flash((
                '{} contains numbers or dates that Notify cannot understand. '
                'Try formatting all columns as ‘text’ or export your file as CSV.'
            ).format(
                form.file.data.filename
            ))

    column_headings = get_spreadsheet_column_headings_from_template(template)

    return render_template(
        'views/send.html',
        template=template,
        column_headings=list(ascii_uppercase[:len(column_headings)]),
        example=[column_headings, get_example_csv_rows(template)],
        form=form,
        allowed_file_extensions=Spreadsheet.ALLOWED_FILE_EXTENSIONS
    )


@main.route("/services/<uuid:service_id>/send/<uuid:template_id>.csv", methods=['GET'])
@user_has_permissions('send_messages', 'manage_templates')
def get_example_csv(service_id, template_id):
    template = get_template(
        service_api_client.get_service_template(service_id, template_id)['data'], current_service
    )
    return Spreadsheet.from_rows([
        get_spreadsheet_column_headings_from_template(template),
        get_example_csv_rows(template)
    ]).as_csv_data, 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'inline; filename="{}.csv"'.format(template.name)
    }


@main.route("/services/<uuid:service_id>/send/<uuid:template_id>/set-sender", methods=['GET', 'POST'])
@user_has_permissions('send_messages', restrict_admin_usage=True)
def set_sender(service_id, template_id):
    session['sender_id'] = None
    redirect_to_one_off = redirect(
        url_for('.send_one_off', service_id=service_id, template_id=template_id)
    )

    template = current_service.get_template_with_user_permission_or_403(template_id, current_user)

    if template['template_type'] == 'letter':
        return redirect_to_one_off

    sender_details = get_sender_details(service_id, template['template_type'])

    if len(sender_details) == 1:
        session['sender_id'] = sender_details[0]['id']

    if len(sender_details) <= 1:
        return redirect_to_one_off

    sender_context = get_sender_context(sender_details, template['template_type'])

    form = SetSenderForm(
        sender=sender_context['default_id'],
        sender_choices=sender_context['value_and_label'],
        sender_label=sender_context['description']
    )
    option_hints = {sender_context['default_id']: '(Default)'}
    if sender_context.get('receives_text_message', None):
        option_hints.update({sender_context['receives_text_message']: '(Receives replies)'})
    if sender_context.get('default_and_receives', None):
        option_hints = {sender_context['default_and_receives']: '(Default and receives replies)'}

    # extend all radios that need hint text
    form.sender.param_extensions = {'items': []}
    for item_id, _item_value in form.sender.choices:
        if item_id in option_hints:
            extensions = {'hint': {'text': option_hints[item_id]}}
        else:
            extensions = {}  # if no extensions needed, send an empty dict to preserve order of items
        form.sender.param_extensions['items'].append(extensions)

    if form.validate_on_submit():
        session['sender_id'] = form.sender.data
        return redirect(url_for('.send_one_off',
                                service_id=service_id,
                                template_id=template_id))

    return render_template(
        'views/templates/set-sender.html',
        form=form,
        template_id=template_id,
        sender_context={'title': sender_context['title'], 'description': sender_context['description']},
        option_hints=option_hints
    )


def get_sender_context(sender_details, template_type):
    context = {
        'email': {
            'title': 'Where should replies come back to?',
            'description': 'Where should replies come back to?',
            'field_name': 'email_address'
        },
        'letter': {
            'title': 'Send to one recipient',
            'description': 'What should appear in the top right of the letter?',
            'field_name': 'contact_block'
        },
        'sms': {
            'title': 'Who should the message come from?',
            'description': 'Who should the message come from?',
            'field_name': 'sms_sender'
        }
    }[template_type]

    sender_format = context['field_name']

    context['default_id'] = next(sender['id'] for sender in sender_details if sender['is_default'])
    if template_type == 'sms':
        inbound = [sender['id'] for sender in sender_details if sender['inbound_number_id']]
        if inbound:
            context['receives_text_message'] = next(iter(inbound))
        if context['default_id'] == context.get('receives_text_message', None):
            context['default_and_receives'] = context['default_id']

    context['value_and_label'] = [(sender['id'], nl2br(sender[sender_format])) for sender in sender_details]
    return context


def get_sender_details(service_id, template_type):
    api_call = {
        'email': service_api_client.get_reply_to_email_addresses,
        'letter': service_api_client.get_letter_contacts,
        'sms': service_api_client.get_sms_senders
    }[template_type]
    return api_call(service_id)


@main.route("/services/<uuid:service_id>/send/<uuid:template_id>/one-off")
@user_has_permissions('send_messages', restrict_admin_usage=True)
def send_one_off(service_id, template_id):
    session['recipient'] = None
    session['placeholders'] = {}

    db_template = current_service.get_template_with_user_permission_or_403(template_id, current_user)
    if db_template['template_type'] == 'letter':
        session['sender_id'] = None
        return redirect(
            url_for('.send_one_off_letter_address', service_id=service_id, template_id=template_id)
        )

    if db_template['template_type'] not in current_service.available_template_types:
        return redirect(url_for(
            '.action_blocked',
            service_id=service_id,
            notification_type=db_template['template_type'],
            return_to='view_template',
            template_id=template_id))

    return redirect(url_for(
        '.send_one_off_step',
        service_id=service_id,
        template_id=template_id,
        step_index=0,
    ))


def get_notification_check_endpoint(service_id, template):
    return redirect(url_for(
        'main.check_notification',
        service_id=service_id,
        template_id=template.id,
    ))


@main.route(
    "/services/<uuid:service_id>/send/<uuid:template_id>/one-off/address",
    methods=['GET', 'POST']
)
@user_has_permissions('send_messages', restrict_admin_usage=True)
def send_one_off_letter_address(service_id, template_id):
    if {'recipient', 'placeholders'} - set(session.keys()):
        # if someone has come here via a bookmark or back button they might have some stuff still in their session
        return redirect(url_for('.send_one_off', service_id=service_id, template_id=template_id))

    db_template = current_service.get_template_with_user_permission_or_403(template_id, current_user)

    template = get_template(
        db_template,
        current_service,
        show_recipient=True,
        letter_preview_url=url_for(
            'no_cookie.send_test_preview',
            service_id=service_id,
            template_id=template_id,
            filetype='png',
        ),
        page_count=get_page_count_for_letter(db_template),
        email_reply_to=None,
        sms_sender=None
    )

    current_session_address = PostalAddress.from_personalisation(
        get_normalised_placeholders_from_session()
    )

    form = LetterAddressForm(
        address=current_session_address.normalised,
        allow_international_letters=current_service.has_permission('international_letters'),
    )

    if form.validate_on_submit():
        session['placeholders'].update(PostalAddress(form.address.data).as_personalisation)

        placeholders = fields_to_fill_in(template)
        if all_placeholders_in_session(placeholders):
            return get_notification_check_endpoint(service_id, template)

        first_non_address_placeholder_index = len(address_lines_1_to_7_keys)

        return redirect(url_for(
            'main.send_one_off_step',
            service_id=service_id,
            template_id=template_id,
            step_index=first_non_address_placeholder_index,
        ))

    return render_template(
        'views/send-one-off-letter-address.html',
        page_title=get_send_test_page_title(
            template_type='letter',
            entering_recipient=True,
            name=template.name,
        ),
        template=template,
        form=form,
        back_link=get_back_link(service_id, template, 0),
        link_to_upload=True,
    )


@main.route(
    "/services/<uuid:service_id>/send/<uuid:template_id>/one-off/step-<int:step_index>",
    methods=['GET', 'POST'],
)
@user_has_permissions('send_messages', restrict_admin_usage=True)
def send_one_off_step(service_id, template_id, step_index):
    if {'recipient', 'placeholders'} - set(session.keys()):
        return redirect(url_for(
            ".send_one_off",
            service_id=service_id,
            template_id=template_id,
        ))

    db_template = current_service.get_template_with_user_permission_or_403(template_id, current_user)

    email_reply_to = None
    sms_sender = None
    if db_template['template_type'] == 'email':
        email_reply_to = get_email_reply_to_address_from_session()
    elif db_template['template_type'] == 'sms':
        sms_sender = get_sms_sender_from_session()

    template_values = get_recipient_and_placeholders_from_session(db_template['template_type'])

    template = get_template(
        db_template,
        current_service,
        show_recipient=True,
        letter_preview_url=url_for(
            'no_cookie.send_test_preview',
            service_id=service_id,
            template_id=template_id,
            filetype='png',
        ),
        page_count=get_page_count_for_letter(db_template, values=template_values),
        email_reply_to=email_reply_to,
        sms_sender=sms_sender
    )

    placeholders = fields_to_fill_in(template)

    try:
        current_placeholder = placeholders[step_index]
    except IndexError:
        if all_placeholders_in_session(placeholders):
            return get_notification_check_endpoint(service_id, template)
        return redirect(url_for(
            '.send_one_off',
            service_id=service_id,
            template_id=template_id,
        ))

    # if we're in a letter, we should show address block rather than "address line #" or "postcode"
    if template.template_type == 'letter':
        if step_index < len(address_lines_1_to_7_keys):
            return redirect(url_for(
                '.send_one_off_letter_address',
                service_id=service_id,
                template_id=template_id,
            ))
        if current_placeholder in Columns(PostalAddress('').as_personalisation):
            return redirect(url_for(
                request.endpoint,
                service_id=service_id,
                template_id=template_id,
                step_index=step_index + 1,
            ))

    form = get_placeholder_form_instance(
        current_placeholder,
        dict_to_populate_from=get_normalised_placeholders_from_session(),
        template_type=template.template_type,
        allow_international_phone_numbers=current_service.has_permission('international_sms'),
    )

    if form.validate_on_submit():
        # if it's the first input (phone/email), we store against `recipient` as well, for easier extraction.
        # Only if it's not a letter.
        # And only if we're not on the test route, since that will already have the user's own number set
        if (
            step_index == 0
            and template.template_type != 'letter'
        ):
            session['recipient'] = form.placeholder_value.data

        session['placeholders'][current_placeholder] = form.placeholder_value.data

        if all_placeholders_in_session(placeholders):
            return get_notification_check_endpoint(service_id, template)

        return redirect(url_for(
            request.endpoint,
            service_id=service_id,
            template_id=template_id,
            step_index=step_index + 1,
        ))

    back_link = get_back_link(service_id, template, step_index, placeholders)

    template.values = template_values
    template.values[current_placeholder] = None

    return render_template(
        'views/send-test.html',
        page_title=get_send_test_page_title(
            template.template_type,
            entering_recipient=not session['recipient'],
            name=template.name,
        ),
        template=template,
        form=form,
        skip_link=get_skip_link(step_index, template),
        back_link=back_link,
        link_to_upload=(
            request.endpoint == 'main.send_one_off_step'
            and step_index == 0
        ),
    )


@no_cookie.route("/services/<uuid:service_id>/send/<uuid:template_id>/test.<filetype>", methods=['GET'])
@user_has_permissions('send_messages')
def send_test_preview(service_id, template_id, filetype):

    if filetype not in ('pdf', 'png'):
        abort(404)

    db_template = current_service.get_template_with_user_permission_or_403(template_id, current_user)

    template = get_template(
        db_template,
        current_service,
        letter_preview_url=url_for(
            'no_cookie.send_test_preview',
            service_id=service_id,
            template_id=template_id,
            filetype='png',
        ),
    )

    template.values = get_normalised_placeholders_from_session()

    return TemplatePreview.from_utils_template(template, filetype, page=request.args.get('page'))


@main.route(
    '/services/<uuid:service_id>/send/<uuid:template_id>'
    '/from-contact-list'
)
@user_has_permissions('send_messages')
def choose_from_contact_list(service_id, template_id):
    db_template = current_service.get_template_with_user_permission_or_403(
        template_id, current_user
    )
    template = get_template(
        db_template, current_service,
    )
    return render_template(
        'views/send-contact-list.html',
        contact_lists=ContactListsAlphabetical(
            current_service.id,
            template_type=template.template_type,
        ),
        template=template,
    )


@main.route(
    '/services/<uuid:service_id>/send/<uuid:template_id>'
    '/from-contact-list/<uuid:contact_list_id>'
)
@user_has_permissions('send_messages')
def send_from_contact_list(service_id, template_id, contact_list_id):
    contact_list = ContactList.from_id(
        contact_list_id,
        service_id=current_service.id,
    )
    return redirect(url_for(
        'main.check_messages',
        service_id=current_service.id,
        template_id=template_id,
        upload_id=contact_list.copy_to_uploads(),
        contact_list_id=contact_list.id,
    ))


def _check_messages(service_id, template_id, upload_id, preview_row, letters_as_pdf=False):

    try:
        # The happy path is that the job doesn’t already exist, so the
        # API will return a 404 and the client will raise HTTPError.
        job_api_client.get_job(service_id, upload_id)

        # the job exists already - so go back to the templates page
        # If we just return a `redirect` (302) object here, we'll get
        # errors when we try and unpack in the check_messages route.
        # Rasing a werkzeug.routing redirect means that doesn't happen.
        raise PermanentRedirect(url_for(
            'main.send_messages',
            service_id=service_id,
            template_id=template_id
        ))
    except HTTPError as e:
        if e.status_code != 404:
            raise

    statistics = service_api_client.get_service_statistics(service_id, today_only=True)
    remaining_messages = (current_service.message_limit - sum(stat['requested'] for stat in statistics.values()))

    contents = s3download(service_id, upload_id)

    db_template = current_service.get_template_with_user_permission_or_403(template_id, current_user)

    email_reply_to = None
    sms_sender = None
    if db_template['template_type'] == 'email':
        email_reply_to = get_email_reply_to_address_from_session()
    elif db_template['template_type'] == 'sms':
        sms_sender = get_sms_sender_from_session()

    template = get_template(
        db_template,
        current_service,
        show_recipient=True,
        letter_preview_url=url_for(
            'no_cookie.check_messages_preview',
            service_id=service_id,
            template_id=template_id,
            upload_id=upload_id,
            filetype='png',
            row_index=preview_row,
        ) if not letters_as_pdf else None,
        email_reply_to=email_reply_to,
        sms_sender=sms_sender,
        page_count=get_page_count_for_letter(db_template),
    )
    recipients = RecipientCSV(
        contents,
        template=template,
        max_initial_rows_shown=50,
        max_errors_shown=50,
        whitelist=itertools.chain.from_iterable(
            [user.name, user.mobile_number, user.email_address] for user in Users(service_id)
        ) if current_service.trial_mode else None,
        remaining_messages=remaining_messages,
        allow_international_sms=current_service.has_permission('international_sms'),
        allow_international_letters=current_service.has_permission('international_letters'),
    )

    if request.args.get('from_test'):
        # only happens if generating a letter preview test
        back_link = url_for('main.send_one_off', service_id=service_id, template_id=template.id)
        choose_time_form = None
    else:
        back_link = url_for('main.send_messages', service_id=service_id, template_id=template.id)
        choose_time_form = ChooseTimeForm()

    if preview_row < 2:
        abort(404)

    if preview_row < len(recipients) + 2:
        template.values = recipients[preview_row - 2].recipient_and_personalisation
    elif preview_row > 2:
        abort(404)

    page_count = get_page_count_for_letter(db_template, template.values)
    original_file_name = get_csv_metadata(service_id, upload_id).get('original_file_name', '')

    return dict(
        recipients=recipients,
        template=template,
        errors=recipients.has_errors,
        row_errors=get_errors_for_csv(recipients, template.template_type),
        count_of_recipients=len(recipients),
        count_of_displayed_recipients=len(list(recipients.displayed_rows)),
        original_file_name=original_file_name,
        upload_id=upload_id,
        form=CsvUploadForm(),
        remaining_messages=remaining_messages,
        choose_time_form=choose_time_form,
        back_link=back_link,
        trying_to_send_letters_in_trial_mode=all((
            current_service.trial_mode,
            template.template_type == 'letter',
        )),
        first_recipient_column=recipients.recipient_column_headers[0],
        preview_row=preview_row,
        sent_previously=job_api_client.has_sent_previously(
            service_id, template.id, db_template['version'], original_file_name
        ),
        letter_too_long=is_letter_too_long(page_count),
        letter_max_pages=LETTER_MAX_PAGE_COUNT,
        letter_min_address_lines=PostalAddress.MIN_LINES,
        letter_max_address_lines=PostalAddress.MAX_LINES,
        page_count=page_count
    )


@main.route("/services/<uuid:service_id>/<uuid:template_id>/check/<uuid:upload_id>", methods=['GET'])
@main.route(
    "/services/<uuid:service_id>/<uuid:template_id>/check/<uuid:upload_id>/row-<int:row_index>",
    methods=['GET']
)
@user_has_permissions('send_messages', restrict_admin_usage=True)
def check_messages(service_id, template_id, upload_id, row_index=2):

    data = _check_messages(service_id, template_id, upload_id, row_index)
    data['allowed_file_extensions'] = Spreadsheet.ALLOWED_FILE_EXTENSIONS

    if (
        data['recipients'].too_many_rows
        or not data['count_of_recipients']
        or not data['recipients'].has_recipient_columns
        or data['recipients'].duplicate_recipient_column_headers
        or data['recipients'].missing_column_headers
        or data['sent_previously']
    ):
        return render_template('views/check/column-errors.html', **data)

    if data['row_errors']:
        return render_template('views/check/row-errors.html', **data)

    if (
        data['errors']
        or data['trying_to_send_letters_in_trial_mode']
    ):
        return render_template('views/check/column-errors.html', **data)

    metadata_kwargs = {
        'notification_count': data['count_of_recipients'],
        'template_id': template_id,
        'valid': True,
        'original_file_name': data.get('original_file_name', ''),
    }

    if session.get('sender_id') and data['template'].template_type != 'letter':
        # sender_id is not an option for sending letters.
        metadata_kwargs['sender_id'] = session['sender_id']

    set_metadata_on_csv_upload(service_id, upload_id, **metadata_kwargs)

    return render_template('views/check/ok.html', **data)


@no_cookie.route(
    "/services/<uuid:service_id>/<uuid:template_id>/check/<uuid:upload_id>.<filetype>",
    methods=['GET'],
)
@no_cookie.route(
    "/services/<uuid:service_id>/<uuid:template_id>/check/<uuid:upload_id>/row-<int:row_index>.<filetype>",
    methods=['GET'],
)
@user_has_permissions('send_messages')
def check_messages_preview(service_id, template_id, upload_id, filetype, row_index=2):
    if filetype == 'pdf':
        page = None
    elif filetype == 'png':
        page = request.args.get('page', 1)
    else:
        abort(404)

    template = _check_messages(
        service_id, template_id, upload_id, row_index, letters_as_pdf=True
    )['template']
    return TemplatePreview.from_utils_template(template, filetype, page=page)


@no_cookie.route(
    "/services/<uuid:service_id>/<uuid:template_id>/check.<filetype>",
    methods=['GET'],
)
@user_has_permissions('send_messages')
def check_notification_preview(service_id, template_id, filetype):
    if filetype == 'pdf':
        page = None
    elif filetype == 'png':
        page = request.args.get('page', 1)
    else:
        abort(404)

    template = _check_notification(
        service_id, template_id,
    )['template']
    return TemplatePreview.from_utils_template(template, filetype, page=page)


@main.route("/services/<uuid:service_id>/start-job/<uuid:upload_id>", methods=['POST'])
@user_has_permissions('send_messages', restrict_admin_usage=True)
def start_job(service_id, upload_id):

    job_api_client.create_job(
        upload_id,
        service_id,
        scheduled_for=request.form.get('scheduled_for', ''),
        contact_list_id=request.form.get('contact_list_id', ''),
    )

    session.pop('sender_id', None)

    return redirect(
        url_for(
            'main.view_job',
            job_id=upload_id,
            service_id=service_id,
            just_sent='yes',
        )
    )


@main.route("/services/<uuid:service_id>/end-tour/<uuid:example_template_id>")
@user_has_permissions('manage_templates')
def go_to_dashboard_after_tour(service_id, example_template_id):

    service_api_client.delete_service_template(service_id, example_template_id)

    return redirect(
        url_for('main.service_dashboard', service_id=service_id)
    )


def fields_to_fill_in(template, prefill_current_user=False):

    if 'letter' == template.template_type:
        return letter_address_columns + list(template.placeholders)

    if not prefill_current_user:
        return first_column_headings[template.template_type] + list(template.placeholders)

    if template.template_type == 'sms':
        session['recipient'] = current_user.mobile_number
        session['placeholders']['phone number'] = current_user.mobile_number
    else:
        session['recipient'] = current_user.email_address
        session['placeholders']['email address'] = current_user.email_address

    return list(template.placeholders)


def get_normalised_placeholders_from_session():
    return Columns(session.get('placeholders', {}))


def get_recipient_and_placeholders_from_session(template_type):
    placeholders = get_normalised_placeholders_from_session()

    if template_type == 'sms':
        placeholders['phone_number'] = session['recipient']
    else:
        placeholders['email_address'] = session['recipient']

    return placeholders


def all_placeholders_in_session(placeholders):
    return all(
        get_normalised_placeholders_from_session().get(placeholder, False) not in (False, None)
        for placeholder in placeholders
    )


def get_send_test_page_title(template_type, entering_recipient, name=None):
    if entering_recipient:
        return 'Send ‘{}’'.format(name)
    return 'Personalise this message'


def get_back_link(service_id, template, step_index, placeholders=None):
    if step_index == 0:
        if should_skip_template_page(template.template_type):
            return url_for(
                '.choose_template',
                service_id=service_id,
            )
        else:
            return url_for(
                '.view_template',
                service_id=service_id,
                template_id=template.id,
            )

    if template.template_type == 'letter' and placeholders:
        # Make sure we’re not redirecting users to a page which will
        # just redirect them forwards again
        back_link_destination_step_index = next((
            index
            for index, placeholder in reversed(
                list(enumerate(placeholders[:step_index]))
            )
            if placeholder not in Columns(
                PostalAddress('').as_personalisation
            )
        ), 1)
        return get_back_link(service_id, template, back_link_destination_step_index + 1)

    return url_for(
        'main.send_one_off_step',
        service_id=service_id,
        template_id=template.id,
        step_index=step_index - 1,
    )


def get_skip_link(step_index, template):
    if (
        request.endpoint == 'main.send_one_off_step'
        and step_index == 0
        and template.template_type in ("sms", "email")
        and not (template.template_type == 'sms' and current_user.mobile_number is None)
        and current_user.has_permissions('manage_templates', 'manage_service')
    ):
        return (
            'Use my {}'.format(first_column_headings[template.template_type][0]),
            url_for('.send_one_off_to_myself', service_id=current_service.id, template_id=template.id),
        )


@main.route("/services/<uuid:service_id>/template/<uuid:template_id>/one-off/send-to-myself", methods=['GET'])
@user_has_permissions('send_messages', restrict_admin_usage=True)
def send_one_off_to_myself(service_id, template_id):
    db_template = current_service.get_template_with_user_permission_or_403(template_id, current_user)

    if db_template['template_type'] not in ("sms", "email"):
        abort(404)

    # We aren't concerned with creating the exact template (for example adding recipient and sender names)
    # we just want to create enough to use `fields_to_fill_in`
    template = get_template(
        db_template,
        current_service,
    )
    fields_to_fill_in(template, prefill_current_user=True)

    return redirect(url_for(
        'main.send_one_off_step',
        service_id=service_id,
        template_id=template_id,
        step_index=1,
    ))


@main.route("/services/<uuid:service_id>/template/<uuid:template_id>/notification/check", methods=['GET'])
@user_has_permissions('send_messages', restrict_admin_usage=True)
def check_notification(service_id, template_id):
    return render_template(
        'views/notifications/check.html',
        **_check_notification(service_id, template_id),
    )


def _check_notification(service_id, template_id, exception=None):
    db_template = current_service.get_template_with_user_permission_or_403(template_id, current_user)
    email_reply_to = None
    sms_sender = None
    if db_template['template_type'] == 'email':
        email_reply_to = get_email_reply_to_address_from_session()
    elif db_template['template_type'] == 'sms':
        sms_sender = get_sms_sender_from_session()
    template = get_template(
        db_template,
        current_service,
        show_recipient=True,
        email_reply_to=email_reply_to,
        sms_sender=sms_sender,
        letter_preview_url=url_for(
            'no_cookie.check_notification_preview',
            service_id=service_id,
            template_id=template_id,
            filetype='png',
        ),
        page_count=get_page_count_for_letter(db_template),
    )

    placeholders = fields_to_fill_in(template)

    back_link = get_back_link(service_id, template, len(placeholders), placeholders)

    if (
        (
            not session.get('recipient')
            and db_template['template_type'] != 'letter'
        )
        or not all_placeholders_in_session(template.placeholders)
    ):
        raise PermanentRedirect(back_link)

    template.values = get_recipient_and_placeholders_from_session(template.template_type)
    page_count = get_page_count_for_letter(db_template, template.values)
    template.page_count = page_count
    return dict(
        template=template,
        back_link=back_link,
        letter_too_long=is_letter_too_long(page_count),
        letter_max_pages=LETTER_MAX_PAGE_COUNT,
        page_count=page_count,
        **(get_template_error_dict(exception) if exception else {}),
    )


def get_template_error_dict(exception):
    # TODO: Make API return some computer-friendly identifier as well as the end user error messages
    if 'service is in trial mode' in exception.message:
        error = 'not-allowed-to-send-to'
    elif 'Exceeded send limits' in exception.message:
        error = 'too-many-messages'
    # the error from the api is changing for message-too-long, but we need both until the api is deployed.
    elif 'Content for template has a character count greater than the limit of' in exception.message:
        error = 'message-too-long'
    elif 'Text messages cannot be longer than' in exception.message:
        error = 'message-too-long'
    else:
        raise exception

    return {
        'error': error,
        'SMS_CHAR_COUNT_LIMIT': SMS_CHAR_COUNT_LIMIT,
        'current_service': current_service,

        # used to trigger CSV specific err msg content, so not needed for single notification errors.
        'original_file_name': False
    }


@main.route("/services/<uuid:service_id>/template/<uuid:template_id>/notification/check", methods=['POST'])
@user_has_permissions('send_messages', restrict_admin_usage=True)
def send_notification(service_id, template_id):
    if {'recipient', 'placeholders'} - set(session.keys()):
        return redirect(url_for(
            '.send_one_off',
            service_id=service_id,
            template_id=template_id,
        ))

    db_template = current_service.get_template_with_user_permission_or_403(template_id, current_user)

    try:
        noti = notification_api_client.send_notification(
            service_id,
            template_id=db_template['id'],
            recipient=session['recipient'] or Columns(session['placeholders'])['address line 1'],
            personalisation=session['placeholders'],
            sender_id=session['sender_id'] if 'sender_id' in session else None
        )
    except HTTPError as exception:
        current_app.logger.info('Service {} could not send notification: "{}"'.format(
            current_service.id,
            exception.message
        ))
        return render_template(
            'views/notifications/check.html',
            **_check_notification(service_id, template_id, exception),
        )

    session.pop('placeholders')
    session.pop('recipient')
    session.pop('sender_id', None)

    return redirect(url_for(
        '.view_notification',
        service_id=service_id,
        notification_id=noti['id'],
        # used to show the final step of the tour (help=3) or not show
        # a back link on a just sent one off notification (help=0)
        help=request.args.get('help')
    ))


def get_email_reply_to_address_from_session():
    if session.get('sender_id'):
        return current_service.get_email_reply_to_address(
            session['sender_id']
        )['email_address']


def get_sms_sender_from_session():
    if session.get('sender_id'):
        return current_service.get_sms_sender(
            session['sender_id']
        )['sms_sender']


def get_spreadsheet_column_headings_from_template(template):
    column_headings = []

    if template.template_type == 'letter':
        # We want to avoid showing `address line 7` for now
        recipient_columns = letter_address_columns
    else:
        recipient_columns = first_column_headings[template.template_type]

    for column_heading in (
        recipient_columns + list(template.placeholders)
    ):
        if column_heading not in Columns.from_keys(column_headings):
            column_headings.append(column_heading)

    return column_headings
