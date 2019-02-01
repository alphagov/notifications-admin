from flask import abort, current_app
from notifications_utils.field import Field
from werkzeug.utils import cached_property

from app.notify_client.api_key_api_client import api_key_api_client
from app.notify_client.billing_api_client import billing_api_client
from app.notify_client.email_branding_client import email_branding_client
from app.notify_client.inbound_number_client import inbound_number_client
from app.notify_client.invite_api_client import invite_api_client
from app.notify_client.job_api_client import job_api_client
from app.notify_client.letter_branding_client import letter_branding_client
from app.notify_client.organisations_api_client import organisations_client
from app.notify_client.service_api_client import service_api_client
from app.notify_client.template_folder_api_client import (
    template_folder_api_client,
)
from app.notify_client.user_api_client import user_api_client
from app.utils import get_default_sms_sender


class Service():

    ALLOWED_PROPERTIES = {
        'active',
        'contact_link',
        'dvla_organisation',
        'email_branding',
        'email_from',
        'id',
        'inbound_api',
        'letter_contact_block',
        'letter_logo_filename',
        'message_limit',
        'name',
        'organisation_type',
        'permissions',
        'postage',
        'prefix_sms',
        'research_mode',
        'service_callback_api',
    }

    TEMPLATE_TYPES = (
        'sms',
        'email',
        'letter',
    )

    def __init__(self, _dict):
        # in the case of a bad request current service may be `None`
        self._dict = _dict or {}
        if 'permissions' not in self._dict:
            self.permissions = {'email', 'sms', 'letter'}

    def __bool__(self):
        return self._dict != {}

    def __getattr__(self, attr):
        if attr in self.ALLOWED_PROPERTIES:
            return self._dict[attr]
        raise AttributeError('`{}` is not a service attribute'.format(attr))

    def _get_by_id(self, things, id):
        try:
            return next(thing for thing in things if thing['id'] == str(id))
        except StopIteration:
            abort(404)

    def update(self, **kwargs):
        return service_api_client.update_service(self.id, **kwargs)

    def switch_permission(self, permission):
        return self.force_permission(
            permission,
            on=not self.has_permission(permission),
        )

    def force_permission(self, permission, on=False):

        permissions, permission = set(self.permissions), {permission}

        return self.update_permissions(
            permissions | permission if on else permissions - permission,
        )

    def update_permissions(self, permissions):
        return self.update(permissions=list(permissions))

    def toggle_research_mode(self):
        self.update(research_mode=not self.research_mode)

    @property
    def trial_mode(self):
        return self._dict['restricted']

    def has_permission(self, permission):
        return permission in self.permissions

    @cached_property
    def has_jobs(self):
        return job_api_client.has_jobs(self.id)

    @cached_property
    def team_members(self):
        return sorted(
            (
                invite_api_client.get_invites_for_service(service_id=self.id) +
                user_api_client.get_users_for_service(service_id=self.id)
            ),
            key=lambda user: user.email_address,
        )

    @cached_property
    def has_team_members(self):
        return user_api_client.get_count_of_users_with_permission(
            self.id, 'manage_service'
        ) > 1

    @cached_property
    def all_templates(self):

        templates = service_api_client.get_service_templates(self.id)['data']

        return [
            template for template in templates
            if template['template_type'] in self.available_template_types
        ]

    @cached_property
    def all_template_ids(self):
        return {template['id'] for template in self.all_templates}

    def get_templates(self, template_type='all', template_folder_id=None):
        if isinstance(template_type, str):
            template_type = [template_type]
        if template_folder_id:
            template_folder_id = str(template_folder_id)
        return [
            template for template in self.all_templates
            if (set(template_type) & {'all', template['template_type']})
            and template.get('folder') == template_folder_id
        ]

    @property
    def available_template_types(self):
        return list(filter(self.has_permission, self.TEMPLATE_TYPES))

    @property
    def has_templates(self):
        return bool(self.all_templates)

    def has_folders(self):
        return bool(self.all_template_folders)

    @property
    def has_multiple_template_types(self):
        return len({
            template['template_type'] for template in self.all_templates
        }) > 1

    @property
    def has_email_templates(self):
        return len(self.get_templates('email')) > 0

    @property
    def has_sms_templates(self):
        return len(self.get_templates('sms')) > 0

    @cached_property
    def email_reply_to_addresses(self):
        return service_api_client.get_reply_to_email_addresses(self.id)

    @property
    def has_email_reply_to_address(self):
        return bool(self.email_reply_to_addresses)

    @property
    def count_email_reply_to_addresses(self):
        return len(self.email_reply_to_addresses)

    @property
    def default_email_reply_to_address(self):
        return next(
            (
                x['email_address']
                for x in self.email_reply_to_addresses if x['is_default']
            ), None
        )

    def get_email_reply_to_address(self, id):
        return service_api_client.get_reply_to_email_address(self.id, id)

    @property
    def needs_to_add_email_reply_to_address(self):
        return self.has_email_templates and not self.has_email_reply_to_address

    @property
    def shouldnt_use_govuk_as_sms_sender(self):
        return self.organisation_type in {'local', 'nhs'}

    @cached_property
    def sms_senders(self):
        return service_api_client.get_sms_senders(self.id)

    @property
    def sms_senders_with_hints(self):

        def attach_hint(sender):
            hints = []
            if sender['is_default']:
                hints += ["default"]
            if sender['inbound_number_id']:
                hints += ["receives replies"]
            if hints:
                sender['hint'] = "(" + " and ".join(hints) + ")"
            return sender

        return [attach_hint(sender) for sender in self.sms_senders]

    @property
    def default_sms_sender(self):
        return get_default_sms_sender(self.sms_senders)

    @property
    def count_sms_senders(self):
        return len(self.sms_senders)

    @property
    def sms_sender_is_govuk(self):
        return self.default_sms_sender in {'GOVUK', 'None'}

    def get_sms_sender(self, id):
        return service_api_client.get_sms_sender(self.id, id)

    @property
    def needs_to_change_sms_sender(self):
        return all((
            self.has_sms_templates,
            self.shouldnt_use_govuk_as_sms_sender,
            self.sms_sender_is_govuk,
        ))

    @cached_property
    def letter_contact_details(self):
        return service_api_client.get_letter_contacts(self.id)

    @property
    def count_letter_contact_details(self):
        return len(self.letter_contact_details)

    @property
    def default_letter_contact_block(self):
        return next(
            (
                Field(x['contact_block'], html='escape')
                for x in self.letter_contact_details if x['is_default']
            ), None
        )

    def get_letter_contact_block(self, id):
        return service_api_client.get_letter_contact(self.id, id)

    @property
    def go_live_checklist_completed(self):
        return all((
            self.has_team_members,
            self.has_templates,
            not self.needs_to_add_email_reply_to_address,
            not self.needs_to_change_sms_sender,
        ))

    @property
    def go_live_checklist_completed_as_yes_no(self):
        return 'Yes' if self.go_live_checklist_completed else 'No'

    @cached_property
    def free_sms_fragment_limit(self):
        return billing_api_client.get_free_sms_fragment_limit_for_year(self.id) or 0

    @cached_property
    def data_retention(self):
        return service_api_client.get_service_data_retention(self.id)

    def get_data_retention_item(self, id):
        return next(
            (dr for dr in self.data_retention if dr['id'] == id),
            None
        )

    def get_days_of_retention(self, notification_type):
        return next(
            (dr for dr in self.data_retention if dr['notification_type'] == notification_type),
            {}
        ).get('days_of_retention', current_app.config['ACTIVITY_STATS_LIMIT_DAYS'])

    @property
    def email_branding_id(self):
        return self._dict['email_branding']

    @cached_property
    def email_branding(self):
        if self.email_branding_id:
            return email_branding_client.get_email_branding(self.email_branding_id)['email_branding']
        return None

    @cached_property
    def letter_branding(self):
        return letter_branding_client.get_letter_branding().get(
            self.dvla_organisation, '001'
        )

    @cached_property
    def organisation_name(self):
        return organisations_client.get_service_organisation(self.id).get('name', None)

    @cached_property
    def inbound_number(self):
        return inbound_number_client.get_inbound_sms_number_for_service(self.id)['data'].get('number', '')

    @property
    def has_inbound_number(self):
        return bool(self.inbound_number)

    @cached_property
    def all_template_folders(self):
        return sorted(
            template_folder_api_client.get_template_folders(self.id),
            key=lambda folder: folder['name'].lower(),
        )

    @cached_property
    def all_template_folder_ids(self):
        return {folder['id'] for folder in self.all_template_folders}

    def get_template_folders(self, template_type='all', parent_folder_id=None):

        if parent_folder_id:
            parent_folder_id = str(parent_folder_id)

        return [
            folder for folder in self.all_template_folders
            if (
                folder['parent_id'] == parent_folder_id and
                self.is_folder_visible(folder['id'], template_type)
            )
        ]

    def get_template_folder(self, folder_id):
        if folder_id is None:
            return {
                'id': None,
                'name': 'Templates',
                'parent_id': None,
            }
        return self._get_by_id(self.all_template_folders, folder_id)

    def is_folder_visible(self, template_folder_id, template_type='all'):

        if template_type == 'all':
            return True

        if self.get_templates(template_type, template_folder_id):
            return True

        if any(
            self.is_folder_visible(child_folder['id'], template_type)
            for child_folder in self.get_template_folders(template_type, template_folder_id)
        ):
            return True

        return False

    def get_template_folder_path(self, template_folder_id):

        folder = self.get_template_folder(template_folder_id)

        if folder['id'] is None:
            return [folder]

        return self.get_template_folder_path(folder['parent_id']) + [
            self.get_template_folder(folder['id'])
        ]

    def get_template_path(self, template):
        return self.get_template_folder_path(template['folder']) + [
            template,
        ]

    def get_template_folders_and_templates(self, template_type, template_folder_id):
        return (
            self.get_templates(template_type, template_folder_id) +
            self.get_template_folders(template_type, template_folder_id)
        )

    @property
    def count_of_templates_and_folders(self):
        return len(self.all_templates + self.all_template_folders)

    def move_to_folder(self, ids_to_move, move_to):

        ids_to_move = set(ids_to_move)

        template_folder_api_client.move_to_folder(
            service_id=self.id,
            folder_id=move_to,
            template_ids=ids_to_move & self.all_template_ids,
            folder_ids=ids_to_move & self.all_template_folder_ids,
        )

    @cached_property
    def api_keys(self):
        return sorted(
            api_key_api_client.get_api_keys(self.id)['apiKeys'],
            key=lambda key: key['name'].lower(),
        )

    def get_api_key(self, id):
        return self._get_by_id(self.api_keys, id)
