from app.notify_client import NotifyAdminAPIClient


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
