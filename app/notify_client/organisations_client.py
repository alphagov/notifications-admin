from app.notify_client import NotifyAdminAPIClient


class OrganisationsClient(NotifyAdminAPIClient):

    def __init__(self):
        super().__init__("a" * 73, "b")

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.service_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = app.config['ADMIN_CLIENT_SECRET']

    def get_organisation(self, id):
        return self.get(url='/organisation/{}'.format(id))

    def get_organisations(self):
        return self.get(url='/organisation')['organisations']

    def get_letter_organisations(self):
        return self.get(url='/dvla_organisations')

    def create_organisation(self, logo, name, colour):
        data = {
            "logo": logo,
            "name": name,
            "colour": colour
        }
        return self.post(url="/organisation", data=data)

    def update_organisation(self, org_id, logo, name, colour):
        data = {
            "logo": logo,
            "name": name,
            "colour": colour
        }
        return self.post(url="/organisation/{}".format(org_id), data=data)
