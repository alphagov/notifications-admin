from datetime import datetime, timedelta
from string import ascii_uppercase

from dateutil.parser import parse
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from markupsafe import Markup
from notifications_python_client.errors import HTTPError
from notifications_utils.formatters import nl2br
from notifications_utils.recipients import first_column_headings

from app import current_service, service_api_client, template_statistics_client
from app.main import main
from app.main.forms import (
    ChooseTemplateType,
    EmailTemplateForm,
    LetterTemplateForm,
    SearchTemplatesForm,
    SetTemplateSenderForm,
    SMSTemplateForm,
)
from app.main.views.send import get_example_csv_rows, get_sender_details
from app.template_previews import TemplatePreview, get_page_count_for_letter
from app.utils import (
    email_or_sms_not_enabled,
    get_template,
    user_has_permissions,
)

form_objects = {
    'email': EmailTemplateForm,
    'sms': SMSTemplateForm,
    'letter': LetterTemplateForm
}

page_headings = {
    'email': 'email',
    'sms': 'text message'
}


@main.route("/services/<service_id>/templates/<uuid:template_id>")
@login_required
@user_has_permissions('view_activity', 'send_messages')
def view_template(service_id, template_id):
    if not current_user.has_permissions('view_activity'):
        return redirect(url_for(
            '.send_one_off', service_id=service_id, template_id=template_id
        ))
    template = service_api_client.get_service_template(service_id, str(template_id))['data']
    if template["template_type"] == "letter":
        letter_contact_details = service_api_client.get_letter_contacts(service_id)
        default_letter_contact_block_id = next(
            (x['id'] for x in letter_contact_details if x['is_default']), None
        )
    else:
        default_letter_contact_block_id = None
    return render_template(
        'views/templates/template.html',
        template=get_template(
            template,
            current_service,
            expand_emails=True,
            letter_preview_url=url_for(
                '.view_letter_template_preview',
                service_id=service_id,
                template_id=template_id,
                filetype='png',
            ),
            show_recipient=True,
            page_count=get_page_count_for_letter(template),
        ),
        default_letter_contact_block_id=default_letter_contact_block_id,
    )


@main.route("/services/<service_id>/start-tour/<uuid:template_id>")
@login_required
@user_has_permissions('view_activity')
def start_tour(service_id, template_id):

    template = service_api_client.get_service_template(service_id, str(template_id))['data']

    if template['template_type'] != 'sms':
        abort(404)

    return render_template(
        'views/templates/start-tour.html',
        template=get_template(
            template,
            current_service,
            show_recipient=True,
        ),
        help='1',
    )


@main.route("/services/<service_id>/templates")
@main.route("/services/<service_id>/templates/<template_type>")
@login_required
@user_has_permissions('view_activity', 'send_messages')
def choose_template(service_id, template_type='all'):
    templates = service_api_client.get_service_templates(service_id)['data']

    letters_available = (
        'letter' in current_service['permissions'] and
        current_user.has_permissions('view_activity')
    )

    available_template_types = list(filter(None, (
        'email',
        'sms',
        'letter' if letters_available else None,
    )))

    templates = [
        template for template in templates
        if template['template_type'] in available_template_types
    ]

    has_multiple_template_types = len({
        template['template_type'] for template in templates
    }) > 1

    template_nav_items = [
        (label, key, url_for('.choose_template', service_id=current_service['id'], template_type=key), '')
        for label, key in filter(None, [
            ('All', 'all'),
            ('Text message', 'sms'),
            ('Email', 'email'),
            ('Letter', 'letter') if letters_available else None,
        ])
    ]

    templates_on_page = [
        template for template in templates
        if (
            template_type in ['all', template['template_type']] and
            template['template_type'] in available_template_types
        )
    ]

    if current_user.has_permissions('view_activity'):
        page_title = 'Templates'
    else:
        page_title = 'Choose a template'

    return render_template(
        'views/templates/choose.html',
        page_title=page_title,
        templates=templates_on_page,
        show_search_box=(len(templates_on_page) > 7),
        show_template_nav=has_multiple_template_types and (len(templates) > 2),
        template_nav_items=template_nav_items,
        template_type=template_type,
        search_form=SearchTemplatesForm(),
    )


@main.route("/services/<service_id>/templates/<template_id>.<filetype>")
@login_required
@user_has_permissions('view_activity', 'send_messages')
def view_letter_template_preview(service_id, template_id, filetype):
    if filetype not in ('pdf', 'png'):
        abort(404)

    db_template = service_api_client.get_service_template(service_id, template_id)['data']

    return TemplatePreview.from_database_object(db_template, filetype, page=request.args.get('page'))


def _view_template_version(service_id, template_id, version, letters_as_pdf=False):
    return dict(template=get_template(
        service_api_client.get_service_template(service_id, template_id, version=version)['data'],
        current_service,
        expand_emails=True,
        letter_preview_url=url_for(
            '.view_template_version_preview',
            service_id=service_id,
            template_id=template_id,
            version=version,
            filetype='png',
        ) if not letters_as_pdf else None
    ))


@main.route("/services/<service_id>/templates/<template_id>/version/<int:version>")
@login_required
@user_has_permissions('view_activity')
def view_template_version(service_id, template_id, version):
    return render_template(
        'views/templates/template_history.html',
        **_view_template_version(service_id=service_id, template_id=template_id, version=version)
    )


@main.route("/services/<service_id>/templates/<template_id>/version/<int:version>.<filetype>")
@login_required
@user_has_permissions('view_activity')
def view_template_version_preview(service_id, template_id, version, filetype):
    db_template = service_api_client.get_service_template(service_id, template_id, version=version)['data']
    return TemplatePreview.from_database_object(db_template, filetype)


@main.route("/services/<service_id>/templates/add", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates')
def add_template_by_type(service_id):

    form = ChooseTemplateType(
        include_letters='letter' in current_service['permissions']
    )

    if form.validate_on_submit():

        if form.template_type.data == 'letter':
            blank_letter = service_api_client.create_service_template(
                'Untitled',
                'letter',
                'Body',
                service_id,
                'Main heading',
                'normal',
            )
            return redirect(url_for(
                '.view_template',
                service_id=service_id,
                template_id=blank_letter['data']['id'],
            ))

        if email_or_sms_not_enabled(form.template_type.data, current_service['permissions']):
            return redirect(url_for(
                '.action_blocked',
                service_id=service_id,
                notification_type=form.template_type.data,
                return_to='add_new_template',
                template_id='0'
            ))
        else:
            return redirect(url_for(
                '.add_service_template',
                service_id=service_id,
                template_type=form.template_type.data,
            ))

    return render_template('views/templates/add.html', form=form)


@main.route("/services/<service_id>/templates/action-blocked/<notification_type>/<return_to>/<template_id>")
@login_required
@user_has_permissions('manage_templates')
def action_blocked(service_id, notification_type, return_to, template_id):
    if notification_type == 'sms':
        notification_type = 'text messages'
    elif notification_type == 'email':
        notification_type = 'emails'

    return render_template(
        'views/templates/action_blocked.html',
        service_id=service_id,
        notification_type=notification_type,
        return_to=return_to,
        template_id=template_id
    )


@main.route("/services/<service_id>/templates/add-<template_type>", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates')
def add_service_template(service_id, template_type):

    if template_type not in ['sms', 'email', 'letter']:
        abort(404)
    if 'letter' not in current_service['permissions'] and template_type == 'letter':
        abort(403)

    form = form_objects[template_type]()
    if form.validate_on_submit():
        if form.process_type.data == 'priority':
            abort_403_if_not_admin_user()
        try:
            new_template = service_api_client.create_service_template(
                form.name.data,
                template_type,
                form.template_content.data,
                service_id,
                form.subject.data if hasattr(form, 'subject') else None,
                form.process_type.data
            )
        except HTTPError as e:
            if (
                e.status_code == 400 and
                'content' in e.message and
                any(['character count greater than' in x for x in e.message['content']])
            ):
                form.template_content.errors.extend(e.message['content'])
            else:
                raise e
        else:
            return redirect(
                url_for('.view_template', service_id=service_id, template_id=new_template['data']['id'])
            )

    if email_or_sms_not_enabled(template_type, current_service['permissions']):
        return redirect(url_for(
            '.action_blocked',
            service_id=service_id,
            notification_type=template_type,
            return_to='templates',
            template_id='0'
        ))
    else:
        return render_template(
            'views/edit-{}-template.html'.format(template_type),
            form=form,
            template_type=template_type,
            heading_action='Add',
        )


def abort_403_if_not_admin_user():
    if not current_user.platform_admin:
        abort(403)


@main.route("/services/<service_id>/templates/<template_id>/edit", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates')
def edit_service_template(service_id, template_id):
    template = service_api_client.get_service_template(service_id, template_id)['data']
    template['template_content'] = template['content']
    form = form_objects[template['template_type']](**template)

    if form.validate_on_submit():
        if form.process_type.data != template['process_type']:
            abort_403_if_not_admin_user()

        subject = form.subject.data if hasattr(form, 'subject') else None
        new_template = get_template({
            'name': form.name.data,
            'content': form.template_content.data,
            'subject': subject,
            'template_type': template['template_type'],
            'id': template['id'],
            'process_type': form.process_type.data,
            'reply_to_text': template['reply_to_text']
        }, current_service)
        template_change = get_template(template, current_service).compare_to(new_template)
        if template_change.placeholders_added and not request.form.get('confirm'):
            example_column_headings = (
                first_column_headings[new_template.template_type] +
                list(new_template.placeholders)
            )
            return render_template(
                'views/templates/breaking-change.html',
                template_change=template_change,
                new_template=new_template,
                column_headings=list(ascii_uppercase[:len(example_column_headings)]),
                example_rows=[
                    example_column_headings,
                    get_example_csv_rows(new_template),
                    get_example_csv_rows(new_template)
                ],
                form=form
            )
        try:
            service_api_client.update_service_template(
                template_id,
                form.name.data,
                template['template_type'],
                form.template_content.data,
                service_id,
                subject,
                form.process_type.data
            )
        except HTTPError as e:
            if e.status_code == 400:
                if 'content' in e.message and any(['character count greater than' in x for x in e.message['content']]):
                    form.template_content.errors.extend(e.message['content'])
                else:
                    raise e
            else:
                raise e
        else:
            return redirect(url_for(
                '.view_template',
                service_id=service_id,
                template_id=template_id
            ))

    db_template = service_api_client.get_service_template(service_id, template_id)['data']

    if email_or_sms_not_enabled(db_template['template_type'], current_service['permissions']):
        return redirect(url_for(
            '.action_blocked',
            service_id=service_id,
            notification_type=db_template['template_type'],
            return_to='view_template',
            template_id=template_id
        ))
    else:
        return render_template(
            'views/edit-{}-template.html'.format(template['template_type']),
            form=form,
            template_id=template_id,
            template_type=template['template_type'],
            heading_action='Edit'
        )


@main.route("/services/<service_id>/templates/<template_id>/delete", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates')
def delete_service_template(service_id, template_id):
    template = service_api_client.get_service_template(service_id, template_id)['data']

    if request.method == 'POST':
        service_api_client.delete_service_template(service_id, template_id)
        return redirect(url_for(
            '.choose_template',
            service_id=service_id,
        ))

    try:
        last_used_notification = template_statistics_client.get_template_statistics_for_template(
            service_id, template['id']
        )
        message = 'It was last used {} ago'.format(
            'more than seven days' if not last_used_notification else get_human_readable_delta(
                parse(last_used_notification['created_at']).replace(tzinfo=None),
                datetime.utcnow()
            )
        )

    except HTTPError as e:
        if e.status_code == 404:
            message = None
        else:
            raise e

    return render_template(
        'views/templates/template.html',
        template_delete_confirmation_message=(
            'Are you sure you want to delete {}?'.format(template['name']),
            message,
        ),
        template=get_template(
            template,
            current_service,
            expand_emails=True,
            letter_preview_url=url_for(
                '.view_letter_template_preview',
                service_id=service_id,
                template_id=template['id'],
                filetype='png',
            ),
            show_recipient=True,
        ),
    )


@main.route("/services/<service_id>/templates/<template_id>/redact", methods=['GET'])
@login_required
@user_has_permissions('manage_templates')
def confirm_redact_template(service_id, template_id):
    template = service_api_client.get_service_template(service_id, template_id)['data']

    return render_template(
        'views/templates/template.html',
        template=get_template(
            template,
            current_service,
            expand_emails=True,
            letter_preview_url=url_for(
                '.view_letter_template_preview',
                service_id=service_id,
                template_id=template_id,
                filetype='png',
            ),
            show_recipient=True,
        ),
        show_redaction_message=True,
    )


@main.route("/services/<service_id>/templates/<template_id>/redact", methods=['POST'])
@login_required
@user_has_permissions('manage_templates')
def redact_template(service_id, template_id):

    service_api_client.redact_service_template(service_id, template_id)

    flash(
        'Personalised content will be hidden for messages sent with this template',
        'default_with_tick'
    )

    return redirect(url_for(
        '.view_template',
        service_id=service_id,
        template_id=template_id,
    ))


@main.route('/services/<service_id>/templates/<template_id>/versions')
@login_required
@user_has_permissions('view_activity')
def view_template_versions(service_id, template_id):
    return render_template(
        'views/templates/choose_history.html',
        versions=[
            get_template(
                template,
                current_service,
                expand_emails=True,
                letter_preview_url=url_for(
                    '.view_template_version_preview',
                    service_id=service_id,
                    template_id=template_id,
                    version=template['version'],
                    filetype='png',
                )
            )
            for template in service_api_client.get_service_template_versions(service_id, template_id)['data']
        ]
    )


@main.route('/services/<service_id>/templates/<template_id>/set-template-sender', methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates')
def set_template_sender(service_id, template_id):
    template = service_api_client.get_service_template(service_id, template_id)['data']
    sender_details = get_template_sender_form_dict(service_id, template)
    no_senders = sender_details.get('no_senders', False)

    form = SetTemplateSenderForm(
        sender=sender_details['current_choice'],
        sender_choices=sender_details['value_and_label'],
    )
    option_hints = {sender_details['default_sender']: '(Default)'}

    if form.validate_on_submit():
        service_api_client.update_service_template_sender(
            service_id,
            template_id,
            form.sender.data if form.sender.data else None,
        )
        return redirect(url_for('.view_template', service_id=service_id, template_id=template_id))

    return render_template(
        'views/templates/set-template-sender.html',
        form=form,
        template_id=template_id,
        no_senders=no_senders,
        option_hints=option_hints
    )


def get_template_sender_form_dict(service_id, template):
    context = {
        'email': {
            'field_name': 'email_address'
        },
        'letter': {
            'field_name': 'contact_block'
        },
        'sms': {
            'field_name': 'sms_sender'
        }
    }[template['template_type']]

    sender_format = context['field_name']
    service_senders = get_sender_details(service_id, template['template_type'])
    context['default_sender'] = next(
        (x['id'] for x in service_senders if x['is_default']), "Not set"
    )
    if not service_senders:
        context['no_senders'] = True

    context['value_and_label'] = [(sender['id'], Markup(nl2br(sender[sender_format]))) for sender in service_senders]
    context['value_and_label'].insert(0, ('', 'Blank'))  # Add blank option to start of list

    context['current_choice'] = template['service_letter_contact'] if template['service_letter_contact'] else ''
    return context


def get_last_use_message(template_name, template_statistics):
    try:
        most_recent_use = max(
            parse(template_stats['updated_at']).replace(tzinfo=None)
            for template_stats in template_statistics
        )
    except ValueError:
        return '{} has never been used'.format(template_name)

    return '{} was last used {} ago'.format(
        template_name,
        get_human_readable_delta(most_recent_use, datetime.utcnow())
    )


def get_human_readable_delta(from_time, until_time):
    delta = until_time - from_time
    if delta < timedelta(seconds=60):
        return 'under a minute'
    elif delta < timedelta(hours=1):
        minutes = int(delta.seconds / 60)
        return '{} minute{}'.format(minutes, '' if minutes == 1 else 's')
    elif delta < timedelta(days=1):
        hours = int(delta.seconds / 3600)
        return '{} hour{}'.format(hours, '' if hours == 1 else 's')
    else:
        days = delta.days
        return '{} day{}'.format(days, '' if days == 1 else 's')


def should_show_template(template_type):
    return (
        template_type != 'letter' or
        'letter' in current_service['permissions']
    )
