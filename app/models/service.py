from flask import abort, current_app
from notifications_utils.field import Field
from werkzeug.utils import cached_property

from app.models import JSONModel
from app.models.organisation import Organisation
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


class Service(JSONModel):

    ALLOWED_PROPERTIES = {
        'active',
        'contact_link',
        'email_branding',
        'email_from',
        'id',
        'inbound_api',
        'letter_branding',
        'letter_contact_block',
        'message_limit',
        'name',
        'organisation_type',
        'permissions',
        'prefix_sms',
        'research_mode',
        'service_callback_api',
        'volume_email',
        'volume_sms',
        'volume_letter',
        'consent_to_research',
        'count_as_live',
    }

    TEMPLATE_TYPES = (
        'email',
        'sms',
        'letter',
    )

    def __init__(self, _dict):

        super().__init__(_dict)

        if 'permissions' not in self._dict:
            self.permissions = {'email', 'sms', 'letter'}

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
    def invited_users(self):
        return invite_api_client.get_invites_for_service(service_id=self.id)

    @cached_property
    def active_users(self):
        return user_api_client.get_users_for_service(service_id=self.id)

    @cached_property
    def team_members(self):
        return sorted(
            self.invited_users + self.active_users,
            key=lambda user: user.email_address.lower(),
        )

    @cached_property
    def has_team_members(self):
        return user_api_client.get_count_of_users_with_permission(
            self.id, 'manage_service'
        ) > 1

    def cancel_invite(self, invited_user_id):

        if str(invited_user_id) not in {user.id for user in self.invited_users}:
            abort(404)

        return invite_api_client.cancel_invited_user(
            service_id=self.id,
            invited_user_id=str(invited_user_id),
        )

    def get_team_member(self, user_id):

        if str(user_id) not in {user.id for user in self.active_users}:
            abort(404)

        return user_api_client.get_user(user_id)

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

    def get_templates(self, template_type='all', template_folder_id=None, user=None):
        if user and template_folder_id and self.has_permission('edit_folder_permissions'):
            folder = self.get_template_folder(template_folder_id)
            if not user.has_template_folder_permission(folder):
                return []

        if isinstance(template_type, str):
            template_type = [template_type]
        if template_folder_id:
            template_folder_id = str(template_folder_id)
        return [
            template for template in self.all_templates
            if (set(template_type) & {'all', template['template_type']})
            and template.get('folder') == template_folder_id
        ]

    def get_template(self, template_id, version=None):
        return service_api_client.get_service_template(self.id, str(template_id), version)['data']

    def get_template_folder_with_user_permission_or_403(self, folder_id, user):
        template_folder = self.get_template_folder(folder_id)

        if not self.has_permission("edit_folder_permissions"):
            return template_folder

        if not user.has_template_folder_permission(template_folder):
            abort(403)

        return template_folder

    def get_template_with_user_permission_or_403(self, template_id, user):
        template = self.get_template(template_id)

        self.get_template_folder_with_user_permission_or_403(template['folder'], user)

        return template

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
    def has_estimated_usage(self):
        return (
            self.consent_to_research is not None and any((
                self.volume_email,
                self.volume_sms,
                self.volume_letter,
            ))
        )

    @property
    def has_email_templates(self):
        return len(self.get_templates('email')) > 0

    @property
    def has_sms_templates(self):
        return len(self.get_templates('sms')) > 0

    @property
    def intending_to_send_email(self):
        if self.volume_email is None:
            return self.has_email_templates
        return self.volume_email > 0

    @property
    def intending_to_send_sms(self):
        if self.volume_sms is None:
            return self.has_sms_templates
        return self.volume_sms > 0

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
        return self.intending_to_send_email and not self.has_email_reply_to_address

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
            self.intending_to_send_sms,
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
    def volumes(self):
        return sum(filter(None, (
            self.volume_email,
            self.volume_sms,
            self.volume_letter,
        )))

    @property
    def go_live_checklist_completed(self):
        return all((
            bool(self.volumes),
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
    def email_branding_name(self):
        if self.email_branding is None:
            return 'GOV.UK'
        return self.email_branding['name']

    @property
    def letter_branding_id(self):
        return self._dict['letter_branding']

    @cached_property
    def letter_branding(self):
        if self.letter_branding_id:
            return letter_branding_client.get_letter_branding(self.letter_branding_id)
        return None

    @cached_property
    def organisation(self):
        return Organisation(
            organisations_client.get_service_organisation(self.id)
        )

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

    def get_user_template_folders(self, user):
        """Returns a modified list of folders a user has permission to view

        For each folder, we do the following:
        - if user has no permission to view the folder, skip it
        - if folder is visible and its parent is visible, we add it to the list of folders
        we later return without modifying anything
        - if folder is visible, but the parent is not, we iterate through the parent until we
        either find a visible parent or reach root folder. On each iteration we concatenate
        invisible parent folder name to the front of our folder name, modifying the name, and we
        change parent_folder_id attribute to a higher level parent. This flattens the path to the
        folder making sure it displays in the closest visible parent.

        """
        if not self.has_permission("edit_folder_permissions"):
            return self.all_template_folders

        user_folders = []
        for folder in self.all_template_folders:
            if not user.has_template_folder_permission(folder, service=self):
                continue
            parent = self.get_template_folder(folder["parent_id"])
            if user.has_template_folder_permission(parent, service=self):
                user_folders.append(folder)
            else:
                folder_attrs = {
                    "id": folder["id"], "name": folder["name"], "parent_id": folder["parent_id"],
                    "users_with_permission": folder["users_with_permission"]
                }
                while folder_attrs["parent_id"] is not None:
                    folder_attrs["name"] = parent["name"] + " / " + folder_attrs["name"]
                    if parent["parent_id"] is None:
                        folder_attrs["parent_id"] = None
                    else:
                        parent = self.get_template_folder(parent["parent_id"])
                        folder_attrs["parent_id"] = parent.get("id", None)
                        if user.has_template_folder_permission(parent, service=self):
                            break
                user_folders.append(folder_attrs)
        return user_folders

    def get_template_folders(self, template_type='all', parent_folder_id=None, user=None):
        if user:
            folders = self.get_user_template_folders(user)
        else:
            folders = self.all_template_folders
        if parent_folder_id:
            parent_folder_id = str(parent_folder_id)

        return [
            folder for folder in folders
            if (
                folder['parent_id'] == parent_folder_id
                and self.is_folder_visible(folder['id'], template_type, user)
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

    def is_folder_visible(self, template_folder_id, template_type='all', user=None):

        if template_type == 'all':
            return True

        if self.get_templates(template_type, template_folder_id):
            return True

        if any(
            self.is_folder_visible(child_folder['id'], template_type, user)
            for child_folder in self.get_template_folders(template_type, template_folder_id, user)
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
            self.get_templates(template_type, template_folder_id)
            + self.get_template_folders(template_type, template_folder_id)
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

    @property
    def request_to_go_live_tags(self):
        return list(self._get_request_to_go_live_tags())

    def _get_request_to_go_live_tags(self):

        BASE = 'notify_request_to_go_live'

        yield BASE

        if self.go_live_checklist_completed and self.organisation.agreement_signed:
            yield BASE + '_complete'
            return

        for test, tag in (
            (True, ''),
            (not self.volumes, '_volumes'),
            (not self.go_live_checklist_completed, '_checklist'),
            (not self.organisation.agreement_signed, '_mou'),
            (self.needs_to_add_email_reply_to_address, '_email_reply_to'),
            (not self.has_team_members, '_team_member'),
            (not self.has_templates, '_template_content'),
            (self.needs_to_change_sms_sender, '_sms_sender'),
        ):
            if test:
                yield BASE + '_incomplete' + tag
