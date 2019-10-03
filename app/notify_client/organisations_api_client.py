from itertools import chain

from notifications_python_client.errors import HTTPError

from app.extensions import redis_client
from app.notify_client import NotifyAdminAPIClient, _attach_current_user, cache


class OrganisationsClient(NotifyAdminAPIClient):

    @cache.set('organisations')
    def get_organisations(self):
        return self.get(url='/organisations')

    @cache.set('domains')
    def get_domains(self):
        return list(chain.from_iterable(
            organisation['domains']
            for organisation in self.get_organisations()
        ))

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

    @cache.delete('organisations')
    def create_organisation(self, name, crown, organisation_type, agreement_signed):
        return self.post(
            url="/organisations",
            data={
                "name": name,
                "crown": crown,
                "organisation_type": organisation_type,
                "agreement_signed": agreement_signed,
            }
        )

    @cache.delete('domains')
    @cache.delete('organisations')
    def update_organisation(self, org_id, cached_service_ids=None, **kwargs):
        api_response = self.post(url="/organisations/{}".format(org_id), data=kwargs)

        if cached_service_ids:
            redis_client.delete(*map('service-{}'.format, cached_service_ids))

        return api_response

    def update_organisation_name(self, org_id, name):
        return self.update_organisation(org_id, name=name)

    def get_service_organisation(self, service_id):
        return self.get(url="/service/{}/organisation".format(service_id))

    @cache.delete('service-{service_id}')
    @cache.delete('live-service-and-organisation-counts')
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
