from __future__ import unicode_literals
from client.notifications import NotificationsAPIClient


class NotificationsAdminAPIClient(NotificationsAPIClient):

    def create_service(self, service_name, active, limit, restricted):
        """
        Create a service and return the json.
        """
        data = {
            "name": service_name,
            "active": active,
            "limit": limit,
            "restricted": restricted
        }
        return self.post("/service", data)

    def delete_service(self, service_id):
        """
        Delete a service.
        """
        endpoint = "/service/{0}".format(service_id)
        return self.delete(endpoint)

    def update_service(self,
                       service_id,
                       service_name,
                       active,
                       limit,
                       restricted):
        """
        Update a service.
        """
        data = {
            "id": service_id,
            "name": service_name,
            "active": active,
            "limit": limit,
            "restricted": restricted
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

    def delete_service_template(self, service_id, template_id):
        """
        Delete a service template.
        """
        endpoint = "/service/{0}/template/{1}".format(service_id, template_id)
        return self.delete(endpoint)
