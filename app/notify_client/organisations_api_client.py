from itertools import chain

from notifications_python_client.errors import HTTPError

from app.extensions import redis_client
from app.notify_client import NotifyAdminAPIClient, cache


class OrganisationsClient(NotifyAdminAPIClient):
    @cache.set("organisations")
    def get_organisations(self):
        return self.get(url="/organisations")

    @cache.set("domains")
    def get_domains(self):
        return list(chain.from_iterable(organisation["domains"] for organisation in self.get_organisations()))

    def get_organisation(self, org_id):
        return self.get(url="/organisations/{}".format(org_id))

    @cache.set("organisation-{org_id}-name")
    def get_organisation_name(self, org_id):
        return self.get_organisation(org_id)["name"]

    def get_organisation_by_domain(self, domain):
        try:
            return self.get(
                url="/organisations/by-domain?domain={}".format(domain),
            )
        except HTTPError as error:
            if error.status_code == 404:
                return None
            raise error

    @cache.delete("organisations")
    def create_organisation(self, name, crown, organisation_type, agreement_signed):
        return self.post(
            url="/organisations",
            data={
                "name": name,
                "crown": crown,
                "organisation_type": organisation_type,
                "agreement_signed": agreement_signed,
            },
        )

    @cache.delete("domains")
    @cache.delete("organisations")
    def update_organisation(self, org_id, cached_service_ids=None, **kwargs):
        api_response = self.post(url="/organisations/{}".format(org_id), data=kwargs)

        if cached_service_ids:
            redis_client.delete(*map("service-{}".format, cached_service_ids))

        if "name" in kwargs:
            redis_client.delete(f"organisation-{org_id}-name")

        if "email_branding_id" in kwargs and kwargs["email_branding_id"]:
            redis_client.delete(f"organisation-{org_id}-email-branding-pool")

        return api_response

    @cache.delete("organisation-{org_id}-email-branding-pool")
    def add_brandings_to_email_branding_pool(self, org_id, branding_ids):
        return self.post(url=f"/organisations/{org_id}/email-branding-pool", data={"branding_ids": branding_ids})

    @cache.delete("organisation-{org_id}-letter-branding-pool")
    def add_brandings_to_letter_branding_pool(self, org_id, branding_ids):
        return self.post(url=f"/organisations/{org_id}/letter-branding-pool", data={"branding_ids": branding_ids})

    @cache.delete("service-{service_id}")
    @cache.delete("live-service-and-organisation-counts")
    @cache.delete("organisations")
    def update_service_organisation(self, service_id, org_id):
        data = {"service_id": service_id}
        return self.post(url="/organisations/{}/service".format(org_id), data=data)

    def get_organisation_services(self, org_id):
        return self.get(url="/organisations/{}/services".format(org_id))

    @cache.delete("user-{user_id}")
    def remove_user_from_organisation(self, org_id, user_id):
        return self.delete(f"/organisations/{org_id}/users/{user_id}")

    def get_services_and_usage(self, org_id, year):
        return self.get(url=f"/organisations/{org_id}/services-with-usage", params={"year": str(year)})

    @cache.delete("organisations")
    @cache.delete("domains")
    def archive_organisation(self, org_id):
        redis_client.delete(f"organisation-{org_id}-name")

        return self.post(
            url=f"/organisations/{org_id}/archive",
            data=None,
        )

    @cache.set("organisation-{org_id}-email-branding-pool")
    def get_email_branding_pool(self, org_id):
        branding = self.get(
            url=f"/organisations/{org_id}/email-branding-pool",
        )
        return branding["data"]

    @cache.set("organisation-{org_id}-letter-branding-pool")
    def get_letter_branding_pool(self, org_id):
        branding = self.get(
            url=f"/organisations/{org_id}/letter-branding-pool",
        )
        return branding["data"]

    @cache.delete("organisation-{org_id}-email-branding-pool")
    def remove_email_branding_from_pool(self, org_id, branding_id):
        self.delete(f"/organisations/{org_id}/email-branding-pool/{branding_id}")


organisations_client = OrganisationsClient()
