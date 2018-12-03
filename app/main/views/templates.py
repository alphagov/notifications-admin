from datetime import datetime, timedelta
from string import ascii_uppercase

from dateutil.parser import parse
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from markupsafe import Markup
from notifications_python_client.errors import HTTPError
from notifications_utils.formatters import nl2br
from notifications_utils.recipients import first_column_headings

from app import (
    current_service,
    service_api_client,
    template_folder_api_client,
    template_statistics_client,
    user_api_client,
)
from app.main import main
from app.main.forms import (
    ChooseTemplateType,
    EmailTemplateForm,
    LetterTemplateForm,
    SearchTemplatesForm,
    SetTemplateSenderForm,
    SMSTemplateForm,
    TemplateAndFoldersSelectionForm,
    TemplateFolderForm,
)
from app.main.views.send import get_example_csv_rows, get_sender_details
from app.models.service import Service
from app.models.template_list import TemplateList
from app.template_previews import TemplatePreview, get_page_count_for_letter
from app.utils import (
    email_or_sms_not_enabled,
    get_template,
    should_skip_template_page,
    user_has_permissions,
)

form_objects = {
    'email': EmailTemplateForm,
    'sms': SMSTemplateForm,
    'letter': LetterTemplateForm
}


@main.route("/services/<service_id>/templates/<uuid:template_id>")
@login_required
@user_has_permissions()
def view_template(service_id, template_id):
    template = service_api_client.get_service_template(service_id, str(template_id))['data']
    if should_skip_template_page(template['template_type']):
        return redirect(url_for(
            '.send_one_off', service_id=service_id, template_id=template_id
        ))
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


@main.route("/services/<service_id>/templates", methods=['GET', 'POST'])
@main.route("/services/<service_id>/templates/folders/<template_folder_id>", methods=['GET', 'POST'])
@main.route("/services/<service_id>/templates/<template_type>", methods=['GET', 'POST'])
@main.route("/services/<service_id>/templates/<template_type>/folders/<template_folder_id>", methods=['GET', 'POST'])
@login_required
@user_has_permissions()
def choose_template(service_id, template_type='all', template_folder_id=None):

    template_list = TemplateList(current_service, template_type, template_folder_id)

    templates_and_folders_form = TemplateAndFoldersSelectionForm(
        all_template_folders=current_service.all_template_folders,
        template_list=template_list,
        template_type=template_type,
        current_folder_id=template_folder_id,
        allow_adding_letter_template=current_service.has_permission('letter'),
        allow_adding_copy_of_template=(
            current_service.all_templates or
            len(user_api_client.get_service_ids_for_user(current_user)) > 1
        ),
    )

    if request.method == 'POST' and templates_and_folders_form.validate_on_submit():
        if not can_manage_folders():
            abort(403)
        return process_folder_management_form(templates_and_folders_form, template_folder_id)

    return render_template(
        'views/templates/choose.html',
        current_template_folder_id=template_folder_id,
        can_manage_folders=can_manage_folders(),
        template_folder_path=current_service.get_template_folder_path(template_folder_id),
        template_list=template_list,
        show_search_box=current_service.count_of_templates_and_folders > 7,
        show_template_nav=(
            current_service.has_multiple_template_types
            and (len(current_service.all_templates) > 2)
        ),
        template_nav_items=get_template_nav_items(template_folder_id),
        template_type=template_type,
        search_form=SearchTemplatesForm(),
        templates_and_folders_form=templates_and_folders_form
    )


def process_folder_management_form(form, current_folder_id):
    new_folder_id = None

    if form.is_add_template_op:
        return _add_template_by_type(
            form.add_template_by_template_type.data,
            current_folder_id,
        )

    if form.is_add_folder_op:
        new_folder_id = template_folder_api_client.create_template_folder(
            current_service.id,
            name=form.get_folder_name(),
            parent_id=current_folder_id
        )

    if form.is_move_op:
        # if we've just made a folder, we also want to move there
        move_to_id = new_folder_id or form.move_to.data

        current_service.move_to_folder(
            ids_to_move=form.templates_and_folders.data,
            move_to=move_to_id
        )

    return redirect(request.url)


def get_template_nav_label(value):
    return {
        'all': 'All',
        'sms': 'Text message',
        'email': 'Email',
        'letter': 'Letter',
    }[value]


def get_template_nav_items(template_folder_id):
    return [
        (
            get_template_nav_label(key),
            key,
            url_for(
                '.choose_template', service_id=current_service.id,
                template_type=key, template_folder_id=template_folder_id
            ),
            ''
        )
        for key in ['all'] + current_service.available_template_types
    ]


def can_manage_folders():
    return (
        current_service.has_permission('edit_folders') and
        current_user.has_permissions('manage_templates')
    )


@main.route("/services/<service_id>/templates/<template_id>.<filetype>")
@login_required
@user_has_permissions()
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
@user_has_permissions()
def view_template_version(service_id, template_id, version):
    return render_template(
        'views/templates/template_history.html',
        **_view_template_version(service_id=service_id, template_id=template_id, version=version)
    )


@main.route("/services/<service_id>/templates/<template_id>/version/<int:version>.<filetype>")
@login_required
@user_has_permissions()
def view_template_version_preview(service_id, template_id, version, filetype):
    db_template = service_api_client.get_service_template(service_id, template_id, version=version)['data']
    return TemplatePreview.from_database_object(db_template, filetype)


@main.route("/services/<service_id>/templates/add", methods=['GET', 'POST'])
@main.route("/services/<service_id>/templates/folders/<template_folder_id>/add", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates')
def add_template_by_type(service_id, template_folder_id=None):

    form = ChooseTemplateType(
        include_letters=current_service.has_permission('letter'),
        include_copy=(
            current_service.all_templates or
            len(user_api_client.get_service_ids_for_user(current_user)) > 1
        ),
        include_folder=current_service.has_permission('edit_folders')
    )

    if form.validate_on_submit():
        return _add_template_by_type(form.template_type.data, template_folder_id)

    return render_template('views/templates/add.html', form=form)


def _add_template_by_type(template_type, template_folder_id):

    if template_type == 'copy-existing':
        return redirect(url_for(
            '.choose_template_to_copy',
            service_id=current_service.id,
        ))

    if template_type == 'letter':
        blank_letter = service_api_client.create_service_template(
            'Untitled',
            'letter',
            'Body',
            current_service.id,
            'Main heading',
            'normal',
            template_folder_id
        )
        return redirect(url_for(
            '.view_template',
            service_id=current_service.id,
            template_id=blank_letter['data']['id'],
        ))

    if email_or_sms_not_enabled(template_type, current_service.permissions):
        return redirect(url_for(
            '.action_blocked',
            service_id=current_service.id,
            notification_type=template_type,
            return_to='add_new_template',
            template_id='0'
        ))
    else:
        return redirect(url_for(
            '.add_service_template',
            service_id=current_service.id,
            template_type=template_type,
            template_folder_id=template_folder_id,
        ))


@main.route("/services/<service_id>/templates/copy")
@login_required
@user_has_permissions('manage_templates')
def choose_template_to_copy(service_id):
    return render_template(
        'views/templates/copy.html',
        services=[
            Service(service)
            for service in user_api_client.get_services_for_user(current_user)
        ],
    )


@main.route("/services/<service_id>/templates/copy/<uuid:template_id>", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates')
def copy_template(service_id, template_id):

    if not user_api_client.user_belongs_to_service(
        current_user, request.args.get('from_service')
    ):
        abort(403)

    template = service_api_client.get_service_template(
        request.args.get('from_service'),
        str(template_id),
    )['data']

    if request.method == 'POST':
        return add_service_template(service_id, template['template_type'])

    template['template_content'] = template['content']
    template['name'] = _get_template_copy_name(template, current_service.all_templates)
    form = form_objects[template['template_type']](**template)

    return render_template(
        'views/edit-{}-template.html'.format(template['template_type']),
        form=form,
        template_type=template['template_type'],
        heading_action='Add',
        services=user_api_client.get_service_ids_for_user(current_user),
    )


def _get_template_copy_name(template, existing_templates):

    template_names = [existing['name'] for existing in existing_templates]

    for index in reversed(range(1, 10)):
        if '{} (copy {})'.format(template['name'], index) in template_names:
            return '{} (copy {})'.format(template['name'], index + 1)

    if '{} (copy)'.format(template['name']) in template_names:
        return '{} (copy 2)'.format(template['name'])

    return '{} (copy)'.format(template['name'])


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


@main.route("/services/<service_id>/templates/add-folder", methods=['GET', 'POST'])
@main.route("/services/<service_id>/templates/folders/<template_folder_id>/add-folder", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates')
def add_template_folder(service_id, template_folder_id=None):
    if not current_service.has_permission('edit_folders'):
        abort(403)

    form = TemplateFolderForm()

    if form.validate_on_submit():
        template_folder_api_client.create_template_folder(
            current_service.id, name=form.name.data, parent_id=template_folder_id
        )
        return redirect(
            url_for('.choose_template', service_id=service_id, template_folder_id=template_folder_id)
        )

    return render_template(
        'views/templates/add-template-folder.html',
        form=form
    )


@main.route("/services/<service_id>/templates/folders/<template_folder_id>/manage", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates')
def manage_template_folder(service_id, template_folder_id):
    if not current_service.has_permission('edit_folders'):
        abort(403)

    form = TemplateFolderForm(
        name=current_service.get_template_folder(template_folder_id)['name']
    )

    if form.validate_on_submit():
        template_folder_api_client.update_template_folder(
            current_service.id, template_folder_id, name=form.name.data
        )
        return redirect(
            url_for('.choose_template', service_id=service_id, template_folder_id=template_folder_id)
        )

    return render_template(
        'views/templates/manage-template-folder.html',
        form=form,
        template_folder_path=current_service.get_template_folder_path(template_folder_id),
        current_service_id=current_service.id,
        template_folder_id=template_folder_id,
        template_type="all"
    )


@main.route("/services/<service_id>/templates/folders/<template_folder_id>/delete", methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates')
def delete_template_folder(service_id, template_folder_id):

    if not current_service.has_permission('edit_folders'):
        abort(403)

    template_folder = current_service.get_template_folder(template_folder_id)

    form = TemplateFolderForm(name=template_folder['name'])

    if len(current_service.get_template_folders_and_templates(
        template_type="all", template_folder_id=template_folder_id
    )) > 0:
        flash("You must empty this folder before you can delete it".format(template_folder['name']), 'info')
        return redirect(
            url_for(
                '.choose_template', service_id=service_id, template_type="all", template_folder_id=template_folder_id
            )
        )

    if request.method == 'POST':
        try:
            template_folder_api_client.delete_template_folder(current_service.id, template_folder_id)

            return redirect(
                url_for('.choose_template', service_id=service_id, template_folder_id=template_folder['parent_id'])
            )
        except HTTPError as e:
            msg = "Folder is not empty"
            if e.status_code == 400 and msg in e.message:
                flash("You must empty this folder before you can delete it", 'info')
                return redirect(
                    url_for(
                        '.choose_template',
                        service_id=service_id,
                        template_type="all",
                        template_folder_id=template_folder_id
                    )
                )
            else:
                abort(500, e)

    flash("Are you sure you want to delete the ‘{}’ folder?".format(template_folder['name']), 'delete')
    return render_template(
        'views/templates/manage-template-folder.html',
        form=form,
        template_folder_path=current_service.get_template_folder_path(template_folder_id),
        current_service_id=current_service.id,
        template_folder_id=template_folder_id,
        template_type="all",
    )


@main.route("/services/<service_id>/templates/add-<template_type>", methods=['GET', 'POST'])
@main.route("/services/<service_id>/templates/folders/<template_folder_id>/add-<template_type>",
            methods=['GET', 'POST'])
@login_required
@user_has_permissions('manage_templates')
def add_service_template(service_id, template_type, template_folder_id=None):

    if template_type not in ['sms', 'email', 'letter']:
        abort(404)
    if not current_service.has_permission('letter') and template_type == 'letter':
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
                form.process_type.data,
                template_folder_id
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

    if email_or_sms_not_enabled(template_type, current_service.permissions):
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

    if email_or_sms_not_enabled(db_template['template_type'], current_service.permissions):
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
            heading_action='Edit',
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
        message = 'This template was last used {} ago.'.format(
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

    flash(["Are you sure you want to delete ‘{}’?".format(template['name']), message], 'delete')
    return render_template(
        'views/templates/template.html',
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
        current_service.has_permission('letter')
    )
