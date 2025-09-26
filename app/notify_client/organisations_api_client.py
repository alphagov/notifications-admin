from contextvars import ContextVar
from itertools import chain

from flask import current_app, render_template
from notifications_python_client.errors import HTTPError
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.extensions import redis_client
from app.notify_client import NotifyAdminAPIClient, api_client_request_session, cache


class OrganisationsClient(NotifyAdminAPIClient):
    @cache.set("organisations")
    def get_organisations(self):
        return self.get(url="/organisations")

    @cache.set("domains")
    def get_domains(self):
        return list(chain.from_iterable(organisation["domains"] for organisation in self.get_organisations()))

    def get_organisation(self, org_id):
        return self.get(url=f"/organisations/{org_id}")

    @cache.set("organisation-{org_id}-name")
    def get_organisation_name(self, org_id):
        return self.get_organisation(org_id)["name"]

    def get_organisation_by_domain(self, domain):
        try:
            return self.get(
                url=f"/organisations/by-domain?domain={domain}",
            )
        except HTTPError as error:
            if error.status_code == 404:
                return None
            raise error

    def search(self, name):
        return self.get(f"/organisations/search?name={name}")

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
    @cache.delete("organisation-{org_id}-name")
    @cache.delete("organisation-{org_id}-email-branding-pool")
    @cache.delete("organisation-{org_id}-letter-branding-pool")
    def update_organisation(self, org_id, cached_service_ids=None, **kwargs):
        api_response = self.post(url=f"/organisations/{org_id}", data=kwargs)

        if cached_service_ids:
            redis_client.delete(*map("service-{}".format, cached_service_ids))

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
        return self.post(url=f"/organisations/{org_id}/service", data=data)

    def get_organisation_services(self, org_id):
        return self.get(url=f"/organisations/{org_id}/services")

    @cache.delete("user-{user_id}")
    def remove_user_from_organisation(self, org_id, user_id):
        return self.delete(f"/organisations/{org_id}/users/{user_id}")

    def get_services_and_usage(self, org_id, year):
        return self.get(url=f"/organisations/{org_id}/services-with-usage", params={"year": str(year)})

    @cache.delete("organisations")
    @cache.delete("organisation-{org_id}-name")
    @cache.delete("domains")
    def archive_organisation(self, org_id):
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

    @cache.delete("organisation-{org_id}-letter-branding-pool")
    def remove_letter_branding_from_pool(self, org_id, branding_id):
        self.delete(f"/organisations/{org_id}/letter-branding-pool/{branding_id}")

    def notify_users_of_request_to_go_live_for_service(self, service_id):
        self.post(
            url=f"/organisations/notify-users-of-request-to-go-live/{service_id}",
            data=None,
        )

    def notify_org_member_about_next_steps_of_go_live_request(
        self, service_id, service_name, to, check_if_unique: bool, unclear_service_name: bool
    ):
        body = render_template(
            "partials/templates/notify-org-member-about-next-steps-of-go-live-request.md.jinja2",
            check_if_unique=check_if_unique,
            unclear_service_name=unclear_service_name,
        )
        self.post(
            url=f"/organisations/notify-org-member-about-next-steps-of-go-live-request/{service_id}",
            data={"to": to, "service_name": service_name, "body": body},
        )

    def notify_service_member_of_rejected_go_live_request(
        self,
        service_id: str,
        service_member_name: str,
        service_name: str,
        organisation_name: str,
        rejection_reason: str,
        organisation_team_member_name: str,
        organisation_team_member_email: str,
    ):
        self.post(
            url=f"/organisations/notify-service-member-of-rejected-go-live-request/{service_id}",
            data={
                "name": service_member_name,
                "service_name": service_name,
                "organisation_name": organisation_name,
                "reason": rejection_reason,
                "organisation_team_member_name": organisation_team_member_name,
                "organisation_team_member_email": organisation_team_member_email,
            },
        )


_organisations_client_context_var: ContextVar[OrganisationsClient] = ContextVar("organisations_client")
get_organisations_client: LazyLocalGetter[OrganisationsClient] = LazyLocalGetter(
    _organisations_client_context_var,
    lambda: OrganisationsClient(current_app, request_session=api_client_request_session),
)
memo_resetters.append(lambda: get_organisations_client.clear())
organisations_client = LocalProxy(get_organisations_client)
