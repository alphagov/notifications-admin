from app.notify_client import NotifyAdminAPIClient, _attach_current_user


class OrganisationsClient(NotifyAdminAPIClient):

    def __init__(self):
        super().__init__("a" * 73, "b")

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.service_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = app.config['ADMIN_CLIENT_SECRET']

    def get_organisations(self):
        return self.get(url='/organisations')

    def get_organisation(self, org_id):
        return self.get(url='/organisations/{}'.format(org_id))

    def create_organisation(self, name):
        data = {
            "name": name
        }
        return self.post(url="/organisations", data=data)

    def update_organisation(self, org_id, name):
        data = {
            "name": name
        }
        return self.post(url="/organisations/{}".format(org_id), data=data)

    def get_service_organisation(self, service_id):
        return self.get(url="/service/{}/organisation".format(service_id))

    def update_service_organisation(self, service_id, org_id):
        data = {
            'service_id': service_id
        }
        return self.post(
            url="/organisations/{}/service".format(org_id),
            data=data
        )

    def get_organisation_services(self, org_id):
        return self.get(url="/organisations/{}/services".format(org_id))

    def remove_user_from_organisation(self, org_id, user_id):
        endpoint = '/organisations/{}/users/{}'.format(
            org_id=org_id,
            user_id=user_id)
        data = _attach_current_user({})
        return self.delete(endpoint, data)
