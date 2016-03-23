from __future__ import unicode_literals
from notifications_python_client.notifications import NotificationsAPIClient


class ServiceAPIClient(NotificationsAPIClient):

    # Fudge assert in the super __init__ so
    # we can set those variables later.
    def __init__(self):
        super(ServiceAPIClient, self).__init__("api_url",
                                               "client",
                                               "secret")

    def init_app(self, application):
        self.base_url = application.config['API_HOST_NAME']
        self.client_id = application.config['ADMIN_CLIENT_USER_NAME']
        self.secret = application.config['ADMIN_CLIENT_SECRET']

    def create_service(self, service_name, active, limit, restricted, user_id):
        """
        Create a service and return the json.
        """
        data = {
            "name": service_name,
            "active": active,
            "limit": limit,
            "user_id": user_id,
            "restricted": restricted
        }
        return self.post("/service", data)['data']['id']

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
        return self.post(endpoint, data)

    def remove_user_from_service(self, service_id, user_id):
        """
        Remove a user from a service
        """
        endpoint = '/service/{service_id}/users/{user_id}'.format(
            service_id=service_id,
            user_id=user_id)
        return self.delete(endpoint)

    def create_service_template(self, name, type_, content, service_id, subject=None):
        """
        Create a service template.
        """
        data = {
            "name": name,
            "template_type": type_,
            "content": content,
            "service": service_id
        }
        if subject:
            data.update({
                'subject': subject
            })
        endpoint = "/service/{0}/template".format(service_id)
        return self.post(endpoint, data)

    def update_service_template(self, id_, name, type_, content, service_id, subject=None):
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
        endpoint = "/service/{0}/template/{1}".format(service_id, id_)
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
