import itertools
from string import ascii_uppercase

from contextlib import suppress
from zipfile import BadZipFile
from xlrd.biffh import XLRDError
from werkzeug.routing import RequestRedirect

from flask import (
    request,
    render_template,
    redirect,
    url_for,
    flash,
    abort,
    session,
    current_app,
)

from flask_login import login_required, current_user

from notifications_utils.columns import Columns
from notifications_utils.recipients import (
    RecipientCSV,
    first_column_headings,
    optional_address_columns,
)

from app.main import main
from app.main.forms import (
    CsvUploadForm,
    ChooseTimeForm,
    get_placeholder_form_instance
)
from app.main.uploader import (
    s3upload,
    s3download
)
from app import job_api_client, service_api_client, current_service, user_api_client, notification_api_client
from app.utils import (
    user_has_permissions,
    get_errors_for_csv,
    Spreadsheet,
    get_help_argument,
    get_template
)
from app.template_previews import TemplatePreview, get_page_count_for_letter


def get_page_headings(template_type):
    return {
        'email': 'Email templates',
        'sms': 'Text message templates',
        'letter': 'Letter templates'
    }[template_type]


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
            for key in first_column_headings['letter']
        ]
    }[template.template_type] + get_example_csv_fields(template.placeholders, use_example_as_example, submitted_fields)


def get_example_letter_address(key):
    return {
        'address line 1': 'A. Name',
        'address line 2': '123 Example Street',
        'postcode': 'XM4 5HQ'
    }.get(key, '')


@main.route("/services/<service_id>/send/<template_id>/csv", methods=['GET', 'POST'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def send_messages(service_id, template_id):

    db_template = service_api_client.get_service_template(service_id, template_id)['data']

    template = get_template(
        db_template,
        current_service,
        show_recipient=True,
        expand_emails=True,
        letter_preview_url=url_for(
            '.view_letter_template_preview',
            service_id=service_id,
            template_id=template_id,
            filetype='png',
            page_count=get_page_count_for_letter(db_template),
        ),
    )

    form = CsvUploadForm()
    if form.validate_on_submit():
        try:
            upload_id = s3upload(
                service_id,
                Spreadsheet.from_file(form.file.data, filename=form.file.data.filename).as_dict,
                current_app.config['AWS_REGION']
            )
            session['upload_data'] = {
                "template_id": template_id,
                "original_file_name": form.file.data.filename
            }
            return redirect(url_for('.check_messages',
                                    service_id=service_id,
                                    upload_id=upload_id,
                                    template_type=template.template_type))
        except (UnicodeDecodeError, BadZipFile, XLRDError):
            flash('Couldn’t read {}. Try using a different file format.'.format(
                form.file.data.filename
            ))

    column_headings = first_column_headings[template.template_type] + list(template.placeholders)

    return render_template(
        'views/send.html',
        template=template,
        column_headings=list(ascii_uppercase[:len(column_headings)]),
        example=[column_headings, get_example_csv_rows(template)],
        form=form
    )


@main.route("/services/<service_id>/send/<template_id>.csv", methods=['GET'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters', 'manage_templates', any_=True)
def get_example_csv(service_id, template_id):
    template = get_template(
        service_api_client.get_service_template(service_id, template_id)['data'], current_service
    )
    return Spreadsheet.from_rows([
        first_column_headings[template.template_type] + list(template.placeholders),
        get_example_csv_rows(template)
    ]).as_csv_data, 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'inline; filename="{}.csv"'.format(template.name)
    }


@main.route("/services/<service_id>/send/<template_id>/test", endpoint='send_test')
@main.route("/services/<service_id>/send/<template_id>/one-off", endpoint='send_one_off')
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def send_test(service_id, template_id):
    session['recipient'] = None
    session['placeholders'] = {}
    session['send_test_letter_page_count'] = None
    return redirect(url_for(
        {
            'main.send_test': '.send_test_step',
            'main.send_one_off': '.send_one_off_step',
        }[request.endpoint],
        service_id=service_id,
        template_id=template_id,
        step_index=0,
        help=get_help_argument(),
    ))


def get_notification_check_endpoint(service_id, template):
    if template.template_type == 'letter':
        return make_and_upload_csv_file(service_id, template)
    else:
        return redirect(url_for(
            'main.check_notification',
            service_id=service_id,
            template_id=template.id,
        ))


@main.route(
    "/services/<service_id>/send/<template_id>/test/step-<int:step_index>",
    methods=['GET', 'POST'],
    endpoint='send_test_step',
)
@main.route(
    "/services/<service_id>/send/<template_id>/one-off/step-<int:step_index>",
    methods=['GET', 'POST'],
    endpoint='send_one_off_step',
)
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def send_test_step(service_id, template_id, step_index):
    if {'recipient', 'placeholders'} - set(session.keys()):
        return redirect(url_for(
            {
                'main.send_test_step': '.send_test',
                'main.send_one_off_step': '.send_one_off',
            }[request.endpoint],
            service_id=service_id,
            template_id=template_id,
        ))

    db_template = service_api_client.get_service_template(service_id, template_id)['data']

    if not session.get('send_test_letter_page_count'):
        session['send_test_letter_page_count'] = get_page_count_for_letter(db_template)

    template = get_template(
        db_template,
        current_service,
        show_recipient=True,
        expand_emails=True,
        letter_preview_url=url_for(
            '.send_test_preview',
            service_id=service_id,
            template_id=template_id,
            filetype='png',
        ),
        page_count=session['send_test_letter_page_count']
    )

    placeholders = fields_to_fill_in(
        template,
        prefill_current_user=(request.endpoint == 'main.send_test_step'),
    )

    try:
        current_placeholder = placeholders[step_index]
    except IndexError:
        if all_placeholders_in_session(placeholders):
            return get_notification_check_endpoint(service_id, template)
        return redirect(url_for(
            {
                'main.send_test_step': '.send_test',
                'main.send_one_off_step': '.send_one_off',
            }[request.endpoint],
            service_id=service_id,
            template_id=template_id,
        ))

    optional_placeholder = (current_placeholder in optional_address_columns)
    form = get_placeholder_form_instance(
        current_placeholder,
        dict_to_populate_from=get_normalised_placeholders_from_session(),
        optional_placeholder=optional_placeholder,
        allow_international_phone_numbers='international_sms' in current_service['permissions'],
    )

    if form.validate_on_submit():
        # if it's the first input (phone/email), we store against `recipient` as well, for easier extraction.
        # Only if it's not a letter.
        # And only if we're not on the test route, since that will already have the user's own number set
        if (
            step_index == 0 and
            template.template_type != 'letter' and
            request.endpoint != 'main.send_test_step'
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
            help=get_help_argument(),
        ))

    back_link = get_back_link(service_id, template_id, step_index)

    template.values = get_receipient_and_placeholders_from_session(template.template_type)
    template.values[current_placeholder] = None

    if (
        request.endpoint == 'main.send_one_off_step' and
        step_index == 0 and
        template.template_type != 'letter'
    ):
        skip_link = (
            'Use my {}'.format(first_column_headings[template.template_type][0]),
            url_for('.send_test', service_id=service_id, template_id=template.id),
        )
    else:
        skip_link = None

    return render_template(
        'views/send-test.html',
        page_title=get_send_test_page_title(template.template_type, get_help_argument()),
        template=template,
        form=form,
        skip_link=skip_link,
        optional_placeholder=optional_placeholder,
        back_link=back_link,
        help=get_help_argument(),
    )


@main.route("/services/<service_id>/send/<template_id>/test.<filetype>", methods=['GET'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def send_test_preview(service_id, template_id, filetype):

    if filetype not in ('pdf', 'png'):
        abort(404)

    db_template = service_api_client.get_service_template(service_id, template_id)['data']

    template = get_template(
        db_template,
        current_service,
        letter_preview_url=url_for(
            '.send_test_preview',
            service_id=service_id,
            template_id=template_id,
            filetype='png',
        ),
    )

    template.values = get_normalised_placeholders_from_session()

    return TemplatePreview.from_utils_template(template, filetype, page=request.args.get('page'))


def _check_messages(service_id, template_type, upload_id, letters_as_pdf=False):

    if not session.get('upload_data'):
        # if we just return a `redirect` (302) object here, we'll get errors when we try and unpack in the
        # check_messages route - so raise a werkzeug.routing redirect to ensure that doesn't happen.

        # NOTE: this is a 301 MOVED PERMANENTLY (httpstatus.es/301), so the browser will cache this redirect, and it'll
        # *always* happen for that browser. _check_messages is only used by endpoints that contain `upload_id`, which
        # is a one-time-use id (that ties to a given file in S3 that is already deleted if it's not in the session)
        raise RequestRedirect(get_check_messages_back_url(service_id, template_type))

    users = user_api_client.get_users_for_service(service_id=service_id)

    statistics = service_api_client.get_detailed_service_for_today(service_id)['data']['statistics']
    remaining_messages = (current_service['message_limit'] - sum(stat['requested'] for stat in statistics.values()))

    contents = s3download(service_id, upload_id)

    template = get_template(
        service_api_client.get_service_template(
            service_id,
            session['upload_data'].get('template_id')
        )['data'],
        current_service,
        show_recipient=True,
        letter_preview_url=url_for(
            '.check_messages_preview',
            service_id=service_id,
            template_type=template_type,
            upload_id=upload_id,
            filetype='png',
        ) if not letters_as_pdf else None
    )
    recipients = RecipientCSV(
        contents,
        template_type=template.template_type,
        placeholders=template.placeholders,
        max_initial_rows_shown=50,
        max_errors_shown=50,
        whitelist=itertools.chain.from_iterable(
            [user.name, user.mobile_number, user.email_address] for user in users
        ) if current_service['restricted'] else None,
        remaining_messages=remaining_messages,
        international_sms='international_sms' in current_service['permissions'],
    )

    if request.args.get('from_test'):
        extra_args = {'help': 1} if request.args.get('help', '0') != '0' else {}
        if len(template.placeholders) or template.template_type == 'letter':
            back_link = url_for(
                '.send_test', service_id=service_id, template_id=template.id, **extra_args
            )
        else:
            back_link = url_for(
                '.view_template', service_id=service_id, template_id=template.id, **extra_args
            )
        choose_time_form = None
    else:
        back_link = url_for('.send_messages', service_id=service_id, template_id=template.id)
        choose_time_form = ChooseTimeForm()

    with suppress(StopIteration):
        first_recipient = None
        template.values = next(recipients.rows)
        first_recipient = template.values.get(
            Columns.make_key(recipients.recipient_column_headers[0]),
            ''
        )

    session['upload_data']['notification_count'] = len(list(recipients.rows))
    session['upload_data']['valid'] = not recipients.has_errors
    return dict(
        recipients=recipients,
        first_recipient=first_recipient,
        template=template,
        errors=recipients.has_errors,
        row_errors=get_errors_for_csv(recipients, template.template_type),
        count_of_recipients=session['upload_data']['notification_count'],
        count_of_displayed_recipients=(
            len(list(recipients.initial_annotated_rows_with_errors))
            if any(recipients.rows_with_errors) and not recipients.missing_column_headers else
            len(list(recipients.initial_annotated_rows))
        ),
        original_file_name=session['upload_data'].get('original_file_name'),
        upload_id=upload_id,
        form=CsvUploadForm(),
        remaining_messages=remaining_messages,
        choose_time_form=choose_time_form,
        back_link=back_link,
        help=get_help_argument()
    )


@main.route("/services/<service_id>/<template_type>/check/<upload_id>", methods=['GET'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def check_messages(service_id, template_type, upload_id):
    return render_template(
        'views/check.html',
        **_check_messages(service_id, template_type, upload_id)
    )


@main.route("/services/<service_id>/<template_type>/check/<upload_id>.<filetype>", methods=['GET'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def check_messages_preview(service_id, template_type, upload_id, filetype):
    if filetype not in ('pdf', 'png'):
        abort(404)

    template = _check_messages(
        service_id, template_type, upload_id, letters_as_pdf=True
    )['template']
    return TemplatePreview.from_utils_template(template, filetype)


@main.route("/services/<service_id>/<template_type>/check/<upload_id>", methods=['POST'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def recheck_messages(service_id, template_type, upload_id):

    if not session.get('upload_data'):
        return redirect(url_for('main.choose_template', service_id=service_id))

    return send_messages(service_id, session['upload_data'].get('template_id'))


@main.route("/services/<service_id>/start-job/<upload_id>", methods=['POST'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def start_job(service_id, upload_id):
    upload_data = session['upload_data']

    if request.files or not upload_data.get('valid'):
        # The csv was invalid, validate the csv again
        return send_messages(service_id, upload_data.get('template_id'))

    session.pop('upload_data')

    job_api_client.create_job(
        upload_id,
        service_id,
        upload_data.get('template_id'),
        upload_data.get('original_file_name'),
        upload_data.get('notification_count'),
        scheduled_for=request.form.get('scheduled_for', '')
    )

    return redirect(
        url_for('main.view_job', job_id=upload_id, service_id=service_id, help=request.form.get('help'))
    )


@main.route("/services/<service_id>/end-tour/<example_template_id>")
@login_required
@user_has_permissions('manage_templates')
def go_to_dashboard_after_tour(service_id, example_template_id):

    service_api_client.delete_service_template(service_id, example_template_id)

    return redirect(
        url_for('main.service_dashboard', service_id=service_id)
    )


def get_check_messages_back_url(service_id, template_type):
    if get_help_argument():
        # if the user is on the introductory tour, then they should be redirected back to the beginning of the tour -
        # but to do that we need to find the template_id of the example template. That template *should* be the only
        # template for that service, but it's possible they've opened another tab and deleted it for example. In that
        # case we should just redirect back to the main page as they clearly know what they're doing.
        templates = service_api_client.get_service_templates(service_id)['data']
        if len(templates) == 1:
            return url_for('.send_test', service_id=service_id, template_id=templates[0]['id'], help=1)

    return url_for('main.choose_template', service_id=service_id)


def fields_to_fill_in(template, prefill_current_user=False):

    recipient_columns = first_column_headings[template.template_type]

    if 'letter' == template.template_type or not prefill_current_user:
        return recipient_columns + list(template.placeholders)

    session['recipient'] = current_user.mobile_number if template.template_type == 'sms' else current_user.email_address

    return list(template.placeholders)


def get_normalised_placeholders_from_session():
    return {
        key: ''.join(value or [])
        for key, value in session.get('placeholders', {}).items()
    }


def get_receipient_and_placeholders_from_session(template_type):
    placeholders = get_normalised_placeholders_from_session()

    if template_type == 'sms':
        placeholders['phone_number'] = session['recipient']
    else:
        placeholders['email_address'] = session['recipient']

    return placeholders


def make_and_upload_csv_file(service_id, template):
    upload_id = s3upload(
        service_id,
        Spreadsheet.from_dict(
            session['placeholders'],
            filename=current_app.config['TEST_MESSAGE_FILENAME']
        ).as_dict,
        current_app.config['AWS_REGION'],
    )
    session['upload_data'] = {
        "template_id": template.id,
        "original_file_name": current_app.config['TEST_MESSAGE_FILENAME']
    }
    return redirect(url_for(
        '.check_messages',
        upload_id=upload_id,
        service_id=service_id,
        template_type=template.template_type,
        from_test=True,
        help=2 if get_help_argument() else 0
    ))


def all_placeholders_in_session(placeholders):
    return all(
        get_normalised_placeholders_from_session().get(placeholder, False) not in (False, None)
        for placeholder in placeholders
    )


def get_send_test_page_title(template_type, help_argument):
    if help_argument:
        return 'Example text message'
    if template_type == 'letter':
        return 'Print a test letter'
    return 'Send to one recipient'


def get_back_link(service_id, template_id, step_index):
    if get_help_argument():
        return None
    elif step_index == 0:
        return url_for(
            '.view_template',
            service_id=service_id,
            template_id=template_id,
        )
    else:
        return url_for(
            request.endpoint,
            service_id=service_id,
            template_id=template_id,
            step_index=step_index - 1,
        )


@main.route("/services/<service_id>/template/<template_id>/notification/check", methods=['GET'])
@login_required
@user_has_permissions('manage_templates')
def check_notification(service_id, template_id):
    db_template = service_api_client.get_service_template(service_id, template_id)['data']

    template = get_template(
        db_template,
        current_service,
        show_recipient=True
    )

    # go back to start of process
    back_link = get_back_link(service_id, template_id, 0)

    if (
        (
            not session.get('recipient') or
            not all_placeholders_in_session(template.placeholders)
        )
        and back_link
    ):
        return redirect(back_link)

    template.values = get_receipient_and_placeholders_from_session(template.template_type)

    return render_template(
        'views/notifications/check.html',
        template=template,
        back_link=back_link,
        help=get_help_argument(),
    )


@main.route("/services/<service_id>/template/<template_id>/notification/check", methods=['POST'])
@login_required
@user_has_permissions('manage_templates')
def send_notification(service_id, template_id):
    if {'recipient', 'placeholders'} - set(session.keys()):
        return redirect(url_for(
            '.send_one_off',
            service_id=service_id,
            template_id=template_id,
        ))

    noti = notification_api_client.send_notification(
        service_id,
        template_id=template_id,
        recipient=session['recipient'],
        personalisation=session['placeholders']
    )

    session.pop('placeholders')
    session.pop('recipient')

    return redirect(url_for(
        '.view_notification',
        service_id=service_id,
        notification_id=noti['id']
    ))
