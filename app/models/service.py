from werkzeug.utils import cached_property

from app.notify_client.job_api_client import job_api_client
from app.notify_client.service_api_client import service_api_client
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

    def __getitem__(self, attr):
        raise NotImplementedError(
            'Use current_service.{} instead of current_service[\'{}\']'.format(attr, attr)
        )

    def get(self, attr, default=None):
        try:
            return self._dict[attr]
        except KeyError:
            return default

    @property
    def trial_mode(self):
        return self._dict['restricted']

    def has_permission(self, permission):
        return permission in self.permissions

    @cached_property
    def has_jobs(self):
        return job_api_client.has_jobs(self.id)

    @cached_property
    def has_team_members(self):
        return user_api_client.get_count_of_users_with_permission(
            self.id, 'manage_service'
        ) > 1

    @cached_property
    def templates(self):

        templates = service_api_client.get_service_templates(self.id)['data']

        return [
            template for template in templates
            if template['template_type'] in self.available_template_types
        ]

    def templates_by_type(self, template_type):
        if isinstance(template_type, str):
            template_type = [template_type]
        return [
            template for template in self.templates
            if set(template_type) & {'all', template['template_type']}
        ]

    @property
    def available_template_types(self):
        return [
            channel for channel in ('email', 'sms', 'letter')
            if self.has_permission(channel)
        ]

    @property
    def has_templates(self):
        return len(self.templates) > 0

    @property
    def has_multiple_template_types(self):
        return len({
            template['template_type'] for template in self.templates
        }) > 1

    @property
    def has_email_templates(self):
        return len(self.templates_by_type('email')) > 0

    @property
    def has_sms_templates(self):
        return len(self.templates_by_type('sms')) > 0

    @cached_property
    def has_email_reply_to_address(self):
        return bool(service_api_client.get_reply_to_email_addresses(
            self.id
        ))

    @property
    def needs_to_add_email_reply_to_address(self):
        return self.has_email_templates and not self.has_email_reply_to_address

    @property
    def shouldnt_use_govuk_as_sms_sender(self):
        return self.organisation_type in {'local', 'nhs'}

    @cached_property
    def sms_sender_is_govuk(self):
        return get_default_sms_sender(
            service_api_client.get_sms_senders(self.id)
        ) in {'GOVUK', 'None'}

    @property
    def needs_to_change_sms_sender(self):
        return all((
            self.has_sms_templates,
            self.shouldnt_use_govuk_as_sms_sender,
            self.sms_sender_is_govuk,
        ))

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
