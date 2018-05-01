from __future__ import unicode_literals

from app.notify_client import NotifyAdminAPIClient, _attach_current_user, cache


class ServiceAPIClient(NotifyAdminAPIClient):
    # Fudge assert in the super __init__ so
    # we can set those variables later.
    def __init__(self):
        super().__init__("a" * 73, "b")

    @cache.delete('user-{user_id}')
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

    @cache.set('service-{service_id}')
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

    @cache.delete('service-{service_id}')
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
            'email_branding',
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

    # This method is not cached because it calls through to one which is
    def update_service_with_properties(self, service_id, properties):
        return self.update_service(service_id, **properties)

    @cache.delete('service-{service_id}')
    def archive_service(self, service_id):
        return self.post('/service/{}/archive'.format(service_id), data=None)

    @cache.delete('service-{service_id}')
    def suspend_service(self, service_id):
        return self.post('/service/{}/suspend'.format(service_id), data=None)

    @cache.delete('service-{service_id}')
    def resume_service(self, service_id):
        return self.post('/service/{}/resume'.format(service_id), data=None)

    @cache.delete('service-{service_id}')
    @cache.delete('user-{user_id}')
    def remove_user_from_service(self, service_id, user_id):
        """
        Remove a user from a service
        """
        endpoint = '/service/{service_id}/users/{user_id}'.format(
            service_id=service_id,
            user_id=user_id)
        data = _attach_current_user({})
        return self.delete(endpoint, data)

    @cache.delete('service-{service_id}-templates')
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

    @cache.delete('service-{service_id}-templates')
    @cache.delete('template-{id_}-version-None')
    @cache.delete('template-{id_}-versions')
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

    @cache.delete('service-{service_id}-templates')
    @cache.delete('template-{id_}-version-None')
    @cache.delete('template-{id_}-versions')
    def redact_service_template(self, service_id, id_):
        return self.post(
            "/service/{}/template/{}".format(service_id, id_),
            _attach_current_user(
                {'redact_personalisation': True}
            ),
        )

    @cache.delete('service-{service_id}-templates')
    @cache.delete('template-{template_id}-version-None')
    @cache.delete('template-{template_id}-versions')
    def update_service_template_sender(self, service_id, template_id, reply_to):
        data = {
            'reply_to': reply_to,
        }
        data = _attach_current_user(data)
        return self.post(
            "/service/{0}/template/{1}".format(service_id, template_id),
            data
        )

    @cache.set('template-{template_id}-version-{version}')
    def get_service_template(self, service_id, template_id, version=None):
        """
        Retrieve a service template.
        """
        endpoint = '/service/{service_id}/template/{template_id}'.format(
            service_id=service_id,
            template_id=template_id)
        if version:
            endpoint = '{base}/version/{version}'.format(base=endpoint, version=version)
        return self.get(endpoint)

    @cache.set('template-{template_id}-versions')
    def get_service_template_versions(self, service_id, template_id):
        """
        Retrieve a list of versions for a template
        """
        endpoint = '/service/{service_id}/template/{template_id}/versions'.format(
            service_id=service_id,
            template_id=template_id
        )
        return self.get(endpoint)

    @cache.set('service-{service_id}-templates')
    def get_service_templates(self, service_id):
        """
        Retrieve all templates for service.
        """
        endpoint = '/service/{service_id}/template'.format(
            service_id=service_id)
        return self.get(endpoint)

    # This doesn’t need caching because it calls through to a method which is cached
    def count_service_templates(self, service_id, template_type=None):
        return len([
            template for template in
            self.get_service_templates(service_id)['data']
            if (
                not template_type
                or template['template_type'] == template_type
            )
        ])

    @cache.delete('service-{service_id}-templates')
    @cache.delete('template-{template_id}-version-None')
    @cache.delete('template-{template_id}-versions')
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

    def is_service_name_unique(self, service_id, name, email_from):
        """
        Check that the service name or email from are unique across all services.
        """
        endpoint = "/service/unique"
        params = {"service_id": service_id, "name": name, "email_from": email_from}
        return self.get(url=endpoint, params=params)["result"]

    # Temp access of service history data. Includes service and api key history
    def get_service_history(self, service_id):
        return self.get('/service/{0}/history'.format(service_id))

    def get_monthly_notification_stats(self, service_id, year):
        return self.get(url='/service/{}/notifications/monthly?year={}'.format(service_id, year))

    def get_whitelist(self, service_id):
        return self.get(url='/service/{}/whitelist'.format(service_id))

    @cache.delete('service-{service_id}')
    def update_whitelist(self, service_id, data):
        return self.put(url='/service/{}/whitelist'.format(service_id), data=data)

    def get_inbound_sms(self, service_id, user_number='', page=None):
        return self.get(
            '/service/{}/inbound-sms'.format(
                service_id,
            ),
            params={
                'user_number': user_number,
                'page': page
            }
        )

    def get_most_recent_inbound_sms(self, service_id, page=None):
        return self.get(
            '/service/{}/inbound-sms/most-recent'.format(
                service_id,
            ),
            params={
                'page': page
            }
        )

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

    @cache.delete('service-{service_id}')
    def create_service_inbound_api(self, service_id, url, bearer_token, user_id):
        data = {
            "url": url,
            "bearer_token": bearer_token,
            "updated_by_id": user_id
        }
        return self.post("/service/{}/inbound-api".format(service_id), data)

    @cache.delete('service-{service_id}')
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

    @cache.delete('service-{service_id}')
    def add_reply_to_email_address(self, service_id, email_address, is_default=False):
        return self.post(
            "/service/{}/email-reply-to".format(service_id),
            data={
                "email_address": email_address,
                "is_default": is_default
            }
        )

    @cache.delete('service-{service_id}')
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

    @cache.delete('service-{service_id}')
    def delete_reply_to_email_address(self, service_id, reply_to_email_id):
        return self.post(
            "/service/{}/email-reply-to/{}/archive".format(service_id, reply_to_email_id),
            data=None
        )

    def get_letter_contacts(self, service_id):
        return self.get("/service/{}/letter-contact".format(service_id))

    def get_letter_contact(self, service_id, letter_contact_id):
        return self.get("/service/{}/letter-contact/{}".format(service_id, letter_contact_id))

    @cache.delete('service-{service_id}')
    def add_letter_contact(self, service_id, contact_block, is_default=False):
        return self.post(
            "/service/{}/letter-contact".format(service_id),
            data={
                "contact_block": contact_block,
                "is_default": is_default
            }
        )

    @cache.delete('service-{service_id}')
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

    @cache.delete('service-{service_id}')
    def add_sms_sender(self, service_id, sms_sender, is_default=False, inbound_number_id=None):
        data = {
            "sms_sender": sms_sender,
            "is_default": is_default
        }
        if inbound_number_id:
            data["inbound_number_id"] = inbound_number_id
        return self.post("/service/{}/sms-sender".format(service_id), data=data)

    @cache.delete('service-{service_id}')
    def update_sms_sender(self, service_id, sms_sender_id, sms_sender, is_default=False):
        return self.post(
            "/service/{}/sms-sender/{}".format(service_id, sms_sender_id),
            data={
                "sms_sender": sms_sender,
                "is_default": is_default
            }
        )

    @cache.delete('service-{service_id}')
    def delete_sms_sender(self, service_id, sms_sender_id):
        return self.post(
            "/service/{}/sms-sender/{}/archive".format(service_id, sms_sender_id),
            data=None
        )

    def get_service_callback_api(self, service_id, callback_api_id):
        return self.get(
            "/service/{}/delivery-receipt-api/{}".format(
                service_id, callback_api_id
            )
        )['data']

    @cache.delete('service-{service_id}')
    def update_service_callback_api(self, service_id, url, bearer_token, user_id, callback_api_id):
        data = {
            "url": url,
            "updated_by_id": user_id
        }
        if bearer_token:
            data['bearer_token'] = bearer_token
        return self.post("/service/{}/delivery-receipt-api/{}".format(service_id, callback_api_id), data)

    @cache.delete('service-{service_id}')
    def create_service_callback_api(self, service_id, url, bearer_token, user_id):
        data = {
            "url": url,
            "bearer_token": bearer_token,
            "updated_by_id": user_id
        }
        return self.post("/service/{}/delivery-receipt-api".format(service_id), data)
