from notifications_python_client.errors import HTTPError

from app.notify_client import NotifyAdminAPIClient, _attach_current_user, cache


class OrganisationsClient(NotifyAdminAPIClient):

    def get_organisations(self):
        return self.get(url='/organisations')

    def get_organisation(self, org_id):
        return self.get(url='/organisations/{}'.format(org_id))

    def get_organisation_by_domain(self, domain):
        try:
            return self.get(
                url='/organisations/by-domain?domain={}'.format(domain),
            )
        except HTTPError as error:
            if error.status_code == 404:
                return None
            raise error

    def create_organisation(self, name):
        data = {
            "name": name
        }
        return self.post(url="/organisations", data=data)

    def update_organisation(self, org_id, **kwargs):
        return self.post(url="/organisations/{}".format(org_id), data=kwargs)

    def update_organisation_name(self, org_id, name):
        return self.update_organisation(org_id, name=name)

    def get_service_organisation(self, service_id):
        return self.get(url="/service/{}/organisation".format(service_id))

    @cache.delete('service-{service_id}')
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

    def is_organisation_name_unique(self, org_id, name):
        return self.get(
            url="/organisations/unique",
            params={"org_id": org_id, "name": name}
        )["result"]


organisations_client = OrganisationsClient()
