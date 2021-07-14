from datetime import datetime

from notifications_utils.clients.redis import daily_limit_cache_key

from app.extensions import redis_client
from app.notify_client import NotifyAdminAPIClient, _attach_current_user, cache


class ServiceAPIClient(NotifyAdminAPIClient):

    def _delete_template_cache_for_service(self, service_id):
        redis_client.delete_cache_keys_by_pattern(f"service-{service_id}-template-*")

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
            "email_from": email_from,
        }
        data = _attach_current_user(data)
        return self.post("/service", data)['data']['id']

    @cache.set('service-{service_id}')
    def get_service(self, service_id):
        """
        Retrieve a service.
        """
        return self.get('/service/{0}'.format(service_id))

    def get_service_statistics(self, service_id, limit_days=None):
        return self.get('/service/{0}/statistics'.format(service_id), params={'limit_days': limit_days})['data']

    def get_services(self, params_dict=None):
        """
        Retrieve a list of services.
        """
        return self.get('/service', params=params_dict)

    def find_services_by_name(self, service_name):
        return self.get('/service/find-services-by-name', params={"service_name": service_name})

    def get_live_services_data(self, params_dict=None):
        """
        Retrieve a list of live services data with contact names and notification counts.
        """
        return self.get('/service/live-services-data', params=params_dict)

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
            'active',
            'billing_contact_email_addresses',
            'billing_contact_names',
            'billing_reference',
            'consent_to_research',
            'contact_link',
            'created_by',
            'count_as_live',
            'email_branding',
            'email_from',
            'free_sms_fragment_limit',
            'go_live_at',
            'go_live_user',
            'letter_branding',
            'letter_contact_block',
            'message_limit',
            'name',
            'notes',
            'organisation_type',
            'permissions',
            'prefix_sms',
            'purchase_order_number',
            'rate_limit',
            'reply_to_email_address',
            'research_mode',
            'restricted',
            'sms_sender',
            'volume_email',
            'volume_letter',
            'volume_sms',
        }
        if disallowed_attributes:
            raise TypeError('Not allowed to update service attributes: {}'.format(
                ", ".join(disallowed_attributes)
            ))

        endpoint = "/service/{0}".format(service_id)
        return self.post(endpoint, data)

    @cache.delete('live-service-and-organisation-counts')
    def update_status(self, service_id, live):
        return self.update_service(
            service_id,
            message_limit=250000 if live else 50,
            restricted=(not live),
            go_live_at=str(datetime.utcnow()) if live else None
        )

    @cache.delete('live-service-and-organisation-counts')
    def update_count_as_live(self, service_id, count_as_live):
        return self.update_service(
            service_id,
            count_as_live=count_as_live,
        )

    # This method is not cached because it calls through to one which is
    def update_service_with_properties(self, service_id, properties):
        return self.update_service(service_id, **properties)

    @cache.delete('service-{service_id}')
    @cache.delete('service-{service_id}-templates')
    def archive_service(self, service_id, cached_service_user_ids):
        if cached_service_user_ids:
            redis_client.delete(*map('user-{}'.format, cached_service_user_ids))
        ret = self.post('/service/{}/archive'.format(service_id), data=None)
        self._delete_template_cache_for_service(str(service_id))
        return ret

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
    def create_service_template(self, name, type_, content, service_id, subject=None, process_type='normal',
                                parent_folder_id=None):
        """
        Create a service template.
        """
        data = {
            "name": name,
            "template_type": type_,
            "content": content,
            "service": service_id,
            "process_type": process_type,
        }
        if subject:
            data.update({
                'subject': subject
            })
        if parent_folder_id:
            data.update({
                'parent_folder_id': parent_folder_id
            })
        data = _attach_current_user(data)
        endpoint = "/service/{0}/template".format(service_id)
        return self.post(endpoint, data)

    @cache.delete('service-{service_id}-templates')
    @cache.delete('service-{service_id}-template-{id_}-versions')
    def update_service_template(
        self, id_, name, type_, content, service_id, subject=None, process_type=None
    ):
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
        self._delete_template_cache_for_service(service_id)
        return self.post(endpoint, data)

    @cache.delete('service-{service_id}-templates')
    @cache.delete('service-{service_id}-template-{id_}-versions')
    def redact_service_template(self, service_id, id_):
        ret = self.post(
            "/service/{}/template/{}".format(service_id, id_),
            _attach_current_user(
                {'redact_personalisation': True}
            ),
        )
        self._delete_template_cache_for_service(service_id)
        return ret

    @cache.delete('service-{service_id}-templates')
    @cache.delete('service-{service_id}-template-{template_id}-versions')
    def update_service_template_sender(self, service_id, template_id, reply_to):
        data = {
            'reply_to': reply_to,
        }
        data = _attach_current_user(data)
        ret = self.post(
            "/service/{0}/template/{1}".format(service_id, template_id),
            data
        )
        self._delete_template_cache_for_service(service_id)
        return ret

    @cache.delete('service-{service_id}-templates')
    @cache.delete('service-{service_id}-template-{template_id}-versions')
    def update_service_template_postage(self, service_id, template_id, postage):
        ret = self.post(
            "/service/{0}/template/{1}".format(service_id, template_id),
            _attach_current_user({'postage': postage})
        )
        self._delete_template_cache_for_service(service_id)
        return ret

    @cache.set('service-{service_id}-template-{template_id}-version-{version}')
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

    @cache.set('service-{service_id}-template-{template_id}-versions')
    def get_service_template_versions(self, service_id, template_id):
        """
        Retrieve a list of versions for a template
        """
        endpoint = '/service/{service_id}/template/{template_id}/versions'.format(
            service_id=service_id,
            template_id=template_id
        )
        return self.get(endpoint)

    def get_precompiled_template(self, service_id):
        """
        Returns the precompiled template for a service, creating it if it doesn't already exist
        """
        return self.get('/service/{}/template/precompiled'.format(service_id))

    @cache.set('service-{service_id}-templates')
    def get_service_templates(self, service_id):
        """
        Retrieve all templates for service.
        """
        endpoint = '/service/{service_id}/template?detailed=False'.format(
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
    @cache.delete('service-{service_id}-template-{template_id}-versions')
    def delete_service_template(self, service_id, template_id):
        """
        Set a service template's archived flag to True
        """
        endpoint = "/service/{0}/template/{1}".format(service_id, template_id)
        data = {
            'archived': True
        }
        data = _attach_current_user(data)
        self._delete_template_cache_for_service(service_id)
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
        return self.get('/service/{0}/history'.format(service_id))['data']

    def get_service_service_history(self, service_id):
        return self.get_service_history(service_id)['service_history']

    def get_service_api_key_history(self, service_id):
        return self.get_service_history(service_id)['api_key_history']

    def get_monthly_notification_stats(self, service_id, year):
        return self.get(url='/service/{}/notifications/monthly?year={}'.format(service_id, year))

    def get_guest_list(self, service_id):
        return self.get(url='/service/{}/guest-list'.format(service_id))

    @cache.delete('service-{service_id}')
    def update_guest_list(self, service_id, data):
        return self.put(url='/service/{}/guest-list'.format(service_id), data=data)

    def get_inbound_sms(self, service_id, user_number=''):
        # POST prevents the user phone number leaking into our logs
        return self.post(
            '/service/{}/inbound-sms'.format(
                service_id,
            ),
            data={'phone_number': user_number}
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

    @cache.delete('service-{service_id}')
    def delete_service_inbound_api(self, service_id, callback_api_id):
        return self.delete("/service/{}/inbound-api/{}".format(
            service_id, callback_api_id
        ))

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

    def verify_reply_to_email_address(self, service_id, email_address):
        return self.post(
            "/service/{}/email-reply-to/verify".format(service_id),
            data={"email": email_address}
        )

    @cache.delete('service-{service_id}')
    def add_reply_to_email_address(self, service_id, email_address, is_default=False):
        ret = self.post(
            "/service/{}/email-reply-to".format(service_id),
            data={
                "email_address": email_address,
                "is_default": is_default
            }
        )
        self._delete_template_cache_for_service(service_id)
        return ret

    @cache.delete('service-{service_id}')
    def update_reply_to_email_address(self, service_id, reply_to_email_id, email_address, is_default=False):
        ret = self.post(
            "/service/{}/email-reply-to/{}".format(
                service_id,
                reply_to_email_id,
            ),
            data={
                "email_address": email_address,
                "is_default": is_default
            }
        )
        self._delete_template_cache_for_service(service_id)
        return ret

    @cache.delete('service-{service_id}')
    def delete_reply_to_email_address(self, service_id, reply_to_email_id):
        ret = self.post(
            "/service/{}/email-reply-to/{}/archive".format(service_id, reply_to_email_id),
            data=None
        )
        self._delete_template_cache_for_service(service_id)
        return ret

    def get_letter_contacts(self, service_id):
        return self.get("/service/{}/letter-contact".format(service_id))

    def get_letter_contact(self, service_id, letter_contact_id):
        return self.get("/service/{}/letter-contact/{}".format(service_id, letter_contact_id))

    @cache.delete('service-{service_id}')
    def add_letter_contact(self, service_id, contact_block, is_default=False):
        ret = self.post(
            "/service/{}/letter-contact".format(service_id),
            data={
                "contact_block": contact_block,
                "is_default": is_default
            }
        )
        self._delete_template_cache_for_service(service_id)
        return ret

    @cache.delete('service-{service_id}')
    def update_letter_contact(self, service_id, letter_contact_id, contact_block, is_default=False):
        ret = self.post(
            "/service/{}/letter-contact/{}".format(
                service_id,
                letter_contact_id,
            ),
            data={
                "contact_block": contact_block,
                "is_default": is_default
            }
        )
        self._delete_template_cache_for_service(service_id)
        return ret

    @cache.delete('service-{service_id}')
    def delete_letter_contact(self, service_id, letter_contact_id):
        ret = self.post(
            "/service/{}/letter-contact/{}/archive".format(service_id, letter_contact_id),
            data=None
        )
        self._delete_template_cache_for_service(service_id)
        return ret

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
        ret = self.post("/service/{}/sms-sender".format(service_id), data=data)
        self._delete_template_cache_for_service(service_id)
        return ret

    @cache.delete('service-{service_id}')
    def update_sms_sender(self, service_id, sms_sender_id, sms_sender, is_default=False):
        ret = self.post(
            "/service/{}/sms-sender/{}".format(service_id, sms_sender_id),
            data={
                "sms_sender": sms_sender,
                "is_default": is_default
            }
        )
        self._delete_template_cache_for_service(service_id)
        return ret

    @cache.delete('service-{service_id}')
    def delete_sms_sender(self, service_id, sms_sender_id):
        ret = self.post(
            "/service/{}/sms-sender/{}/archive".format(service_id, sms_sender_id),
            data=None
        )
        self._delete_template_cache_for_service(service_id)
        return ret

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
    def delete_service_callback_api(self, service_id, callback_api_id):
        return self.delete("/service/{}/delivery-receipt-api/{}".format(
            service_id, callback_api_id
        ))

    @cache.delete('service-{service_id}')
    def create_service_callback_api(self, service_id, url, bearer_token, user_id):
        data = {
            "url": url,
            "bearer_token": bearer_token,
            "updated_by_id": user_id
        }
        return self.post("/service/{}/delivery-receipt-api".format(service_id), data)

    @cache.delete('service-{service_id}-data-retention')
    def create_service_data_retention(self, service_id, notification_type, days_of_retention):
        data = {
            "notification_type": notification_type,
            "days_of_retention": days_of_retention
        }

        return self.post("/service/{}/data-retention".format(service_id), data)

    @cache.delete('service-{service_id}-data-retention')
    def update_service_data_retention(self, service_id, data_retention_id, days_of_retention):
        data = {
            "days_of_retention": days_of_retention
        }
        return self.post("/service/{}/data-retention/{}".format(service_id, data_retention_id), data)

    @cache.set('service-{service_id}-data-retention')
    def get_service_data_retention(self, service_id):
        return self.get("/service/{}/data-retention".format(service_id))

    @cache.set('service-{service_id}-returned-letters-statistics')
    def get_returned_letter_statistics(self, service_id):
        return self.get("service/{}/returned-letter-statistics".format(service_id))

    @cache.set('service-{service_id}-returned-letters-summary')
    def get_returned_letter_summary(self, service_id):
        return self.get("service/{}/returned-letter-summary".format(service_id))

    def get_returned_letters(self, service_id, reported_at):
        return self.get("service/{}/returned-letters?reported_at={}".format(service_id, reported_at))

    @cache.delete('service-{service_id}')
    def set_service_broadcast_settings(
        self, service_id, service_mode, broadcast_channel, provider_restriction, cached_service_user_ids
    ):
        """
        service_mode is one of "training" or "live"
        broadcast channel is one of "operator", "test", "severe", "government"
        provider_restriction is one of "all", "three", "o2", "vodafone", "ee"
        """
        if cached_service_user_ids:
            redis_client.delete(*map('user-{}'.format, cached_service_user_ids))

        data = {
            "service_mode": service_mode,
            "broadcast_channel": broadcast_channel,
            "provider_restriction": provider_restriction
        }

        return self.post("/service/{}/set-as-broadcast-service".format(service_id), data)

    def get_notification_count(self, service_id):
        # if cache is not set return 0
        count = redis_client.get(daily_limit_cache_key(service_id)) or 0
        return int(count)


service_api_client = ServiceAPIClient()
