import base64
import io
import json
import os
from datetime import datetime

from dateutil import parser
from flask import (
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    stream_with_context,
    url_for,
)
from flask_login import current_user
from notifications_python_client.errors import APIError
from notifications_utils.letter_timings import (
    get_letter_timings,
    letter_can_be_cancelled,
)
from notifications_utils.pdf import pdf_page_count
from notifications_utils.template import Template, WithSubjectTemplate
from PyPDF2.utils import PdfReadError

from app import (
    current_service,
    format_date_numeric,
    job_api_client,
    notification_api_client,
    service_api_client,
)
from app.main import main
from app.main.forms import SearchNotificationsForm
from app.notify_client.api_key_api_client import KEY_TYPE_TEST
from app.template_previews import get_page_count_for_letter
from app.utils import (
    DELIVERED_STATUSES,
    FAILURE_STATUSES,
    generate_next_dict,
    generate_notifications_csv,
    generate_previous_dict,
    get_help_argument,
    get_letter_printing_statement,
    get_letter_validation_error,
    get_page_from_request,
    get_template,
    parse_filter_args,
    set_status_filters,
    user_has_permissions,
)


@main.route("/services/<uuid:service_id>/notification/<uuid:notification_id>")
@user_has_permissions('view_activity', 'send_messages')
def view_notification(service_id, notification_id):
    notification = notification_api_client.get_notification(service_id, str(notification_id))
    notification['template'].update({'reply_to_text': notification['reply_to_text']})

    personalisation = get_all_personalisation_from_notification(notification)
    error_message = None
    if notification['template']['is_precompiled_letter']:
        try:
            file_contents, metadata = view_letter_notification_as_preview(
                service_id, notification_id, "pdf", with_metadata=True
            )
            page_count = int(
                metadata["page_count"]
            ) if metadata.get("page_count") else pdf_page_count(io.BytesIO(file_contents))
            if notification["status"] == "validation-failed":
                invalid_pages = metadata.get("invalid_pages")
                invalid_pages = json.loads(invalid_pages) if invalid_pages else invalid_pages
                error_message = get_letter_validation_error(
                    metadata.get("message"), invalid_pages, page_count
                )
        except PdfReadError:
            return render_template(
                'views/notifications/invalid_precompiled_letter.html',
                created_at=notification['created_at']
            )
    else:
        page_count = get_page_count_for_letter(notification['template'], values=personalisation)

    if notification.get('postage'):
        if notification["status"] == "validation-failed":
            notification['template']['postage'] = None
        else:
            notification['template']['postage'] = notification['postage']
    template = get_template(
        notification['template'],
        current_service,
        letter_preview_url=url_for(
            '.view_letter_notification_as_preview',
            service_id=service_id,
            notification_id=notification_id,
            filetype='png',
        ),
        page_count=page_count,
        show_recipient=True,
        redact_missing_personalisation=True,
    )
    template.values = personalisation
    if notification['job']:
        job = job_api_client.get_job(service_id, notification['job']['id'])['data']
    else:
        job = None

    letter_print_day = get_letter_printing_statement(notification['status'], notification['created_at'])

    notification_created = parser.parse(notification['created_at']).replace(tzinfo=None)

    show_cancel_button = notification['notification_type'] == 'letter' and \
        letter_can_be_cancelled(notification['status'], notification_created)

    if get_help_argument() or request.args.get('help') == '0':
        # help=0 is set when you’ve just sent a notification. We
        # only want to show the back link when you’ve navigated to a
        # notification, not when you’ve just sent it.
        back_link = None
    elif request.args.get('from_job'):
        back_link = url_for(
            'main.view_job',
            service_id=current_service.id,
            job_id=request.args.get('from_job'),
        )
    else:
        back_link = url_for(
            'main.view_notifications',
            service_id=current_service.id,
            message_type=template.template_type,
            status='sending,delivered,failed',
        )

    return render_template(
        'views/notifications/notification.html',
        finished=(notification['status'] in (DELIVERED_STATUSES + FAILURE_STATUSES)),
        notification_status=notification['status'],
        message=error_message,
        uploaded_file_name='Report',
        template=template,
        job=job,
        updates_url=url_for(
            ".view_notification_updates",
            service_id=service_id,
            notification_id=notification['id'],
            status=request.args.get('status'),
            help=get_help_argument()
        ),
        partials=get_single_notification_partials(notification),
        created_by=notification.get('created_by'),
        created_at=notification['created_at'],
        updated_at=notification['updated_at'],
        help=get_help_argument(),
        estimated_letter_delivery_date=get_letter_timings(
            notification['created_at'],
            postage=notification['postage']
        ).earliest_delivery,
        notification_id=notification['id'],
        postage=notification['postage'],
        can_receive_inbound=(current_service.has_permission('inbound_sms')),
        is_precompiled_letter=notification['template']['is_precompiled_letter'],
        letter_print_day=letter_print_day,
        show_cancel_button=show_cancel_button,
        sent_with_test_key=(
            notification.get('key_type') == KEY_TYPE_TEST
        ),
        back_link=back_link,
    )


@main.route("/services/<uuid:service_id>/notification/<uuid:notification_id>/cancel", methods=['GET', 'POST'])
@user_has_permissions('view_activity', 'send_messages')
def cancel_letter(service_id, notification_id):

    if request.method == 'POST':
        notification_api_client.update_notification_to_cancelled(current_service.id, notification_id)
        return redirect(url_for('main.view_notification', service_id=service_id, notification_id=notification_id))

    flash("Are you sure you want to cancel sending this letter?", 'cancel')
    return view_notification(service_id, notification_id)


def get_preview_error_image():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "static", "images", "preview_error.png")
    with open(path, "rb") as file:
        return file.read()


@main.route("/services/<uuid:service_id>/notification/<uuid:notification_id>.<letter_file_extension:filetype>")
@user_has_permissions('view_activity')
def view_letter_notification_as_preview(
    service_id, notification_id, filetype, with_metadata=False
):
    try:
        preview = notification_api_client.get_notification_letter_preview(
            service_id,
            notification_id,
            filetype,
            page=request.args.get('page')
        )

        display_file = base64.b64decode(preview['content'])
    except APIError:
        display_file = get_preview_error_image()
        preview = {"metadata": {}}

    if with_metadata:
        return display_file, preview['metadata']
    return display_file


@main.route("/services/<uuid:service_id>/notification/<uuid:notification_id>.json")
@user_has_permissions('view_activity', 'send_messages')
def view_notification_updates(service_id, notification_id):
    return jsonify(**get_single_notification_partials(
        notification_api_client.get_notification(service_id, notification_id)
    ))


def get_single_notification_partials(notification):
    return {
        'status': render_template(
            'partials/notifications/status.html',
            notification=notification,
            sent_with_test_key=(
                notification.get('key_type') == KEY_TYPE_TEST
            ),
        ),
    }


def get_all_personalisation_from_notification(notification):

    if notification['template'].get('redact_personalisation'):
        notification['personalisation'] = {}

    if notification['template']['template_type'] == 'email':
        notification['personalisation']['email_address'] = notification['to']

    if notification['template']['template_type'] == 'sms':
        notification['personalisation']['phone_number'] = notification['to']

    return notification['personalisation']


@main.route('/services/<uuid:service_id>/notifications', methods=['GET', 'POST'])
@main.route('/services/<uuid:service_id>/notifications/<template_type:message_type>', methods=['GET', 'POST'])
@user_has_permissions()
def view_notifications(service_id, message_type=None):
    return render_template(
        'views/notifications.html',
        partials=get_notifications(service_id, message_type),
        message_type=message_type,
        status=request.args.get('status') or 'sending,delivered,failed',
        page=request.args.get('page', 1),
        to=request.form.get('to', ''),
        search_form=SearchNotificationsForm(
            message_type=message_type,
            to=request.form.get('to', ''),
        ),
        things_you_can_search_by={
            'email': ['email address'],
            'sms': ['phone number'],
            'letter': [],
            None: ['email address', 'phone number'],
        }.get(message_type) + {
            True: ['reference'],
            False: [],
        }.get(bool(current_service.api_keys)),
        download_link=url_for(
            '.download_notifications_csv',
            service_id=current_service.id,
            message_type=message_type,
            status=request.args.get('status')
        )
    )


@main.route('/services/<uuid:service_id>/notifications.json', methods=['GET', 'POST'])
@main.route('/services/<uuid:service_id>/notifications/<template_type:message_type>.json', methods=['GET', 'POST'])
@user_has_permissions()
def get_notifications_as_json(service_id, message_type=None):
    return jsonify(get_notifications(
        service_id, message_type, status_override=request.args.get('status')
    ))


@main.route("/services/<uuid:service_id>/download-notifications.csv")
@user_has_permissions('view_activity')
def download_notifications_csv(service_id):
    filter_args = parse_filter_args(request.args)
    filter_args['status'] = set_status_filters(filter_args)

    service_data_retention_days = current_service.get_days_of_retention(filter_args.get('message_type')[0])
    return Response(
        stream_with_context(
            generate_notifications_csv(
                service_id=service_id,
                job_id=None,
                status=filter_args.get('status'),
                page=request.args.get('page', 1),
                page_size=10000,
                format_for_csv=True,
                template_type=filter_args.get('message_type'),
                limit_days=service_data_retention_days,
            )
        ),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'inline; filename="{} - {} - {} report.csv"'.format(
                format_date_numeric(datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")),
                filter_args['message_type'][0],
                current_service.name)
        }
    )


@main.route('/services/<uuid:service_id>/notifications.csv', endpoint="view_notifications_csv")
@main.route(
    '/services/<uuid:service_id>/notifications/<template_type:message_type>.csv',
    endpoint="view_notifications_csv"
)
@user_has_permissions()
def get_notifications(service_id, message_type, status_override=None):
    # TODO get the api to return count of pages as well.
    page = get_page_from_request()
    if page is None:
        abort(404, "Invalid page argument ({}).".format(request.args.get('page')))
    filter_args = parse_filter_args(request.args)
    filter_args['status'] = set_status_filters(filter_args)
    service_data_retention_days = None

    if message_type is not None:
        service_data_retention_days = current_service.get_days_of_retention(message_type)

    if request.path.endswith('csv') and current_user.has_permissions('view_activity'):
        return Response(
            generate_notifications_csv(
                service_id=service_id,
                page=page,
                page_size=5000,
                template_type=[message_type],
                status=filter_args.get('status'),
                limit_days=service_data_retention_days
            ),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'inline; filename="notifications.csv"'}
        )
    notifications = notification_api_client.get_notifications_for_service(
        service_id=service_id,
        page=page,
        template_type=[message_type] if message_type else [],
        status=filter_args.get('status'),
        limit_days=service_data_retention_days,
        to=request.form.get('to', ''),
    )
    url_args = {
        'message_type': message_type,
        'status': request.args.get('status')
    }
    prev_page = None

    if 'links' in notifications and notifications['links'].get('prev', None):
        prev_page = generate_previous_dict('main.view_notifications', service_id, page, url_args=url_args)
    next_page = None

    if 'links' in notifications and notifications['links'].get('next', None):
        next_page = generate_next_dict('main.view_notifications', service_id, page, url_args)

    if message_type:
        download_link = url_for(
            '.view_notifications_csv',
            service_id=current_service.id,
            message_type=message_type,
            status=request.args.get('status')
        )
    else:
        download_link = None

    return {
        'service_data_retention_days': service_data_retention_days,
        'counts': render_template(
            'views/activity/counts.html',
            status=request.args.get('status'),
            status_filters=get_status_filters(
                current_service,
                message_type,
                service_api_client.get_service_statistics(
                    service_id,
                    today_only=False,
                    limit_days=service_data_retention_days
                )
            )
        ),
        'notifications': render_template(
            'views/activity/notifications.html',
            notifications=list(add_preview_of_content_to_notifications(
                notifications['notifications']
            )),
            page=page,
            limit_days=service_data_retention_days,
            prev_page=prev_page,
            next_page=next_page,
            status=request.args.get('status'),
            message_type=message_type,
            download_link=download_link,
        ),
    }


def get_status_filters(service, message_type, statistics):
    if message_type is None:
        stats = {
            key: sum(
                statistics[message_type][key]
                for message_type in {'email', 'sms', 'letter'}
            )
            for key in {'requested', 'delivered', 'failed'}
        }
    else:
        stats = statistics[message_type]
    stats['sending'] = stats['requested'] - stats['delivered'] - stats['failed']

    filters = [
        # key, label, option
        ('requested', 'total', 'sending,delivered,failed'),
        ('sending', 'sending', 'sending'),
        ('delivered', 'delivered', 'delivered'),
        ('failed', 'failed', 'failed'),
    ]
    return [
        # return list containing label, option, link, count
        (
            label,
            option,
            url_for(
                '.view_notifications',
                service_id=service.id,
                message_type=message_type,
                status=option
            ),
            stats[key]
        )
        for key, label, option in filters
    ]


def add_preview_of_content_to_notifications(notifications):

    for notification in notifications:

        if notification['template'].get('redact_personalisation'):
            notification['personalisation'] = {}

        if notification['template']['template_type'] == 'sms':
            yield dict(
                preview_of_content=str(Template(
                    notification['template'],
                    notification['personalisation'],
                    redact_missing_personalisation=True,
                )),
                **notification
            )
        else:
            if notification['template']['is_precompiled_letter']:
                notification['template']['subject'] = notification['client_reference']
            yield dict(
                preview_of_content=(
                    WithSubjectTemplate(
                        notification['template'],
                        notification['personalisation'],
                        redact_missing_personalisation=True,
                    ).subject
                ),
                **notification
            )
