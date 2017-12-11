from __future__ import unicode_literals

from flask import url_for
from app.utils import BrowsableItem
from app.notify_client import _attach_current_user, NotifyAdminAPIClient


class ServiceAPIClient(NotifyAdminAPIClient):
    # Fudge assert in the super __init__ so
    # we can set those variables later.
    def __init__(self):
        super().__init__("a" * 73, "b")

    def init_app(self, application):
        self.base_url = application.config['API_HOST_NAME']
        self.service_id = application.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = application.config['ADMIN_CLIENT_SECRET']

    def create_service(
        self,
        service_name,
        organisation_type,
        message_limit,
        restricted,
        user_id,
        email_from,
    ):
        """
        Create a service and return the json.
        """
        data = {
            "name": service_name,
            "organisation_type": organisation_type,
            "active": True,
            "message_limit": message_limit,
            "user_id": user_id,
            "restricted": restricted,
            "email_from": email_from
        }
        data = _attach_current_user(data)
        return self.post("/service", data)['data']['id']

    def get_service(self, service_id):
        return self._get_service(service_id, detailed=False, today_only=False)

    def get_detailed_service(self, service_id):
        return self._get_service(service_id, detailed=True, today_only=False)

    def get_detailed_service_for_today(self, service_id):
        return self._get_service(service_id, detailed=True, today_only=True)

    def _get_service(self, service_id, detailed, today_only):
        """
        Retrieve a service.

        :param detailed - return additional details, including notification statistics
        :param today_only - return statistics only for today. No effect if detailed not passed in
        """
        params = {}
        if detailed:
            params['detailed'] = detailed
        if today_only:
            params['today_only'] = today_only

        return self.get(
            '/service/{0}'.format(service_id),
            params=params)

    def get_services(self, params_dict=None):
        """
        Retrieve a list of services.
        """
        return self.get('/service', params=params_dict)

    def get_active_services(self, params_dict=None):
        """
        Retrieve a list of active services.
        """
        params_dict['only_active'] = True
        return self.get_services(params_dict)

    def update_service(
        self,
        service_id,
        **kwargs
    ):
        """
        Update a service.
        """
        data = _attach_current_user(kwargs)
        disallowed_attributes = set(data.keys()) - {
            'name',
            'message_limit',
            'active',
            'restricted',
            'email_from',
            'reply_to_email_address',
            'research_mode',
            'sms_sender',
            'created_by',
            'branding',
            'organisation',
            'letter_contact_block',
            'dvla_organisation',
            'permissions',
            'organisation_type',
            'free_sms_fragment_limit',
            'prefix_sms',
        }
        if disallowed_attributes:
            raise TypeError('Not allowed to update service attributes: {}'.format(
                ", ".join(disallowed_attributes)
            ))

        endpoint = "/service/{0}".format(service_id)
        return self.post(endpoint, data)

    def update_service_with_properties(self, service_id, properties):
        return self.update_service(service_id, **properties)

    def archive_service(self, service_id):
        return self.post('/service/{}/archive'.format(service_id), data=None)

    def suspend_service(self, service_id):
        return self.post('/service/{}/suspend'.format(service_id), data=None)

    def resume_service(self, service_id):
        return self.post('/service/{}/resume'.format(service_id), data=None)

    def remove_user_from_service(self, service_id, user_id):
        """
        Remove a user from a service
        """
        endpoint = '/service/{service_id}/users/{user_id}'.format(
            service_id=service_id,
            user_id=user_id)
        data = _attach_current_user({})
        return self.delete(endpoint, data)

    def create_service_template(self, name, type_, content, service_id, subject=None, process_type='normal'):
        """
        Create a service template.
        """
        data = {
            "name": name,
            "template_type": type_,
            "content": content,
            "service": service_id,
            "process_type": process_type
        }
        if subject:
            data.update({
                'subject': subject
            })
        data = _attach_current_user(data)
        endpoint = "/service/{0}/template".format(service_id)
        return self.post(endpoint, data)

    def update_service_template(self, id_, name, type_, content, service_id, subject=None, process_type=None):
        """
        Update a service template.
        """
        data = {
            'id': id_,
            'name': name,
            'template_type': type_,
            'content': content,
            'service': service_id
        }
        if subject:
            data.update({
                'subject': subject
            })
        if process_type:
            data.update({
                'process_type': process_type
            })
        data = _attach_current_user(data)
        endpoint = "/service/{0}/template/{1}".format(service_id, id_)
        return self.post(endpoint, data)

    def redact_service_template(self, service_id, id_):
        return self.post(
            "/service/{}/template/{}".format(service_id, id_),
            _attach_current_user(
                {'redact_personalisation': True}
            ),
        )

    def get_service_template(self, service_id, template_id, version=None, *params):
        """
        Retrieve a service template.
        """
        endpoint = '/service/{service_id}/template/{template_id}'.format(
            service_id=service_id,
            template_id=template_id)
        if version:
            endpoint = '{base}/version/{version}'.format(base=endpoint, version=version)
        return self.get(endpoint, *params)

    def get_service_template_versions(self, service_id, template_id, *params):
        """
        Retrieve a list of versions for a template
        """
        endpoint = '/service/{service_id}/template/{template_id}/versions'.format(
            service_id=service_id,
            template_id=template_id
        )
        return self.get(endpoint, *params)

    def get_service_templates(self, service_id, *params):
        """
        Retrieve all templates for service.
        """
        endpoint = '/service/{service_id}/template'.format(
            service_id=service_id)
        return self.get(endpoint, *params)

    def delete_service_template(self, service_id, template_id):
        """
        Set a service template's archived flag to True
        """
        endpoint = "/service/{0}/template/{1}".format(service_id, template_id)
        data = {
            'archived': True
        }
        data = _attach_current_user(data)
        return self.post(endpoint, data=data)

    def is_service_name_unique(self, name, email_from):
        """
        Check that the service name or email from are unique across all services.
        """
        endpoint = "/service/unique"
        params = {"name": name, "email_from": email_from}
        return self.get(url=endpoint, params=params)["result"]

    # Temp access of service history data. Includes service and api key history
    def get_service_history(self, service_id):
        return self.get('/service/{0}/history'.format(service_id))

    def get_monthly_notification_stats(self, service_id, year):
        return self.get(url='/service/{}/notifications/monthly?year={}'.format(service_id, year))

    def get_whitelist(self, service_id):
        return self.get(url='/service/{}/whitelist'.format(service_id))

    def update_whitelist(self, service_id, data):
        return self.put(url='/service/{}/whitelist'.format(service_id), data=data)

    def get_inbound_sms(self, service_id, user_number=''):
        return self.get(
            '/service/{}/inbound-sms?user_number={}'.format(
                service_id,
                user_number,
            )
        )['data']

    def get_inbound_sms_by_id(self, service_id, notification_id):
        return self.get(
            '/service/{}/inbound-sms/{}'.format(
                service_id,
                notification_id,
            )
        )

    def get_inbound_sms_summary(self, service_id):
        return self.get(
            '/service/{}/inbound-sms/summary'.format(service_id)
        )

    def create_service_inbound_api(self, service_id, url, bearer_token, user_id):
        data = {
            "url": url,
            "bearer_token": bearer_token,
            "updated_by_id": user_id
        }
        return self.post("/service/{}/inbound-api".format(service_id), data)

    def update_service_inbound_api(self, service_id, url, bearer_token, user_id, inbound_api_id):
        data = {
            "url": url,
            "updated_by_id": user_id
        }
        if bearer_token:
            data['bearer_token'] = bearer_token
        return self.post("/service/{}/inbound-api/{}".format(service_id, inbound_api_id), data)

    def get_service_inbound_api(self, service_id, inbound_sms_api_id):
        return self.get(
            "/service/{}/inbound-api/{}".format(
                service_id, inbound_sms_api_id
            )
        )['data']

    def get_reply_to_email_addresses(self, service_id):
        return self.get(
            "/service/{}/email-reply-to".format(
                service_id
            )
        )

    def get_reply_to_email_address(self, service_id, reply_to_email_id):
        return self.get(
            "/service/{}/email-reply-to/{}".format(
                service_id,
                reply_to_email_id
            )
        )

    def add_reply_to_email_address(self, service_id, email_address, is_default=False):
        return self.post(
            "/service/{}/email-reply-to".format(service_id),
            data={
                "email_address": email_address,
                "is_default": is_default
            }
        )

    def update_reply_to_email_address(self, service_id, reply_to_email_id, email_address, is_default=False):
        return self.post(
            "/service/{}/email-reply-to/{}".format(
                service_id,
                reply_to_email_id,
            ),
            data={
                "email_address": email_address,
                "is_default": is_default
            }
        )

    def get_letter_contacts(self, service_id):
        return self.get("/service/{}/letter-contact".format(service_id))

    def get_letter_contact(self, service_id, letter_contact_id):
        return self.get("/service/{}/letter-contact/{}".format(service_id, letter_contact_id))

    def add_letter_contact(self, service_id, contact_block, is_default=False):
        return self.post(
            "/service/{}/letter-contact".format(service_id),
            data={
                "contact_block": contact_block,
                "is_default": is_default
            }
        )

    def update_letter_contact(self, service_id, letter_contact_id, contact_block, is_default=False):
        return self.post(
            "/service/{}/letter-contact/{}".format(
                service_id,
                letter_contact_id,
            ),
            data={
                "contact_block": contact_block,
                "is_default": is_default
            }
        )

    def get_aggregate_platform_stats(self, params_dict=None):
        return self.get("/service/platform-stats", params=params_dict)

    def get_sms_senders(self, service_id):
        return self.get(
            "/service/{}/sms-sender".format(service_id)
        )

    def get_sms_sender(self, service_id, sms_sender_id):
        return self.get(
            "/service/{}/sms-sender/{}".format(service_id, sms_sender_id)
        )

    def add_sms_sender(self, service_id, sms_sender, is_default=False, inbound_number_id=None):
        data = {
            "sms_sender": sms_sender,
            "is_default": is_default
        }
        if inbound_number_id:
            data["inbound_number_id"] = inbound_number_id
        return self.post("/service/{}/sms-sender".format(service_id), data=data)

    def update_sms_sender(self, service_id, sms_sender_id, sms_sender, is_default=False):
        return self.post(
            "/service/{}/sms-sender/{}".format(service_id, sms_sender_id),
            data={
                "sms_sender": sms_sender,
                "is_default": is_default
            }
        )

    def get_service_callback_api(self, service_id, callback_api_id):
        return self.get(
            "/service/{}/delivery-receipt-api/{}".format(
                service_id, callback_api_id
            )
        )['data']

    def update_service_callback_api(self, service_id, url, bearer_token, user_id, callback_api_id):
        data = {
            "url": url,
            "updated_by_id": user_id
        }
        if bearer_token:
            data['bearer_token'] = bearer_token
        return self.post("/service/{}/delivery-receipt-api/{}".format(service_id, callback_api_id), data)

    def create_service_callback_api(self, service_id, url, bearer_token, user_id):
        data = {
            "url": url,
            "bearer_token": bearer_token,
            "updated_by_id": user_id
        }
        return self.post("/service/{}/delivery-receipt-api".format(service_id), data)


class ServicesBrowsableItem(BrowsableItem):
    @property
    def title(self):
        return self._item['name']

    @property
    def link(self):
        return url_for('main.service_dashboard', service_id=self._item['id'])

    @property
    def destructive(self):
        return False

    @property
    def hint(self):
        return None
