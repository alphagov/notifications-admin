from app.notify_client import NotifyAdminAPIClient


class OrganisationsClient(NotifyAdminAPIClient):

    def __init__(self):
        super().__init__("a", "b", "c")

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.service_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = app.config['ADMIN_CLIENT_SECRET']

    def get_organisation(self, id):
        return self.get(url='/organisation/{}'.format(id))

    def get_organisations(self):
        return self.get(url='/organisation')['organisations']
