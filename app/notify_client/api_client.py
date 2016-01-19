from __future__ import unicode_literals
from client.notifications import NotificationsAPIClient


class NotificationsAdminAPIClient(NotificationsAPIClient):

    # Fudge assert in the super __init__ so
    # we can set those variables later.
    def __init__(self):
        super(NotificationsAdminAPIClient, self).__init__("api_url",
                                                          "client",
                                                          "secret")

    def init_app(self, application):
        self.base_url = application.config['NOTIFY_API_URL']
        self.client_id = application.config['NOTIFY_API_CLIENT']
        self.secret = application.config['NOTIFY_API_SECRET']

    def create_service(self, service_name, active, limit, restricted, user_id):
        """
        Create a service and return the json.
        """
        data = {
            "name": service_name,
            "active": active,
            "limit": limit,
            "users": [user_id],
            "restricted": restricted
        }
        return self.post("/service", data)

    def delete_service(self, service_id):
        """
        Delete a service.
        """
        endpoint = "/service/{0}".format(service_id)
        return self.delete(endpoint)

    def get_service(self, service_id, *params):
        """
        Retrieve a service.
        """
        return self.get(
            '/service/{0}'.format(service_id))

    def get_services(self, *params):
        """
        Retrieve a list of services.
        """
        return self.get('/service', *params)

    def update_service(self,
                       service_id,
                       service_name,
                       active,
                       limit,
                       restricted,
                       users):
        """
        Update a service.
        """
        data = {
            "id": service_id,
            "name": service_name,
            "active": active,
            "limit": limit,
            "restricted": restricted,
            "users": users
        }
        endpoint = "/service/{0}".format(service_id)
        return self.put(endpoint, update_dict)

    def create_service_template(self, name, type_, content, service_id):
        """
        Create a service template.
        """
        data = {
            "name": name,
            "template_type": type_,
            "content": content,
            "service": service_id
        }
        endpoint = "/service/{0}/template".format(service_id)
        return self.post(endpoint, data)

    def get_service_template(self, service_id, template_id, *params):
        """
        Retrieve a service template.
        """
        endpoint = '/service/{service_id}/template/{template_id}'.format(
            service_id=service_id,
            template_id=template_id)
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
        Delete a service template.
        """
        endpoint = "/service/{0}/template/{1}".format(service_id, template_id)
        return self.delete(endpoint)

    # The implementation of these will change after the notifications-api
    # functionality updates to include the ability to send notifications.
    def send_sms(self,
                 mobile_number,
                 message,
                 job_id=None,
                 description=None):
        pass

    def send_email(self,
                   email_address,
                   message,
                   from_address,
                   subject,
                   job_id=None,
                   description=None):
        pass
