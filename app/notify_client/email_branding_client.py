from app.notify_client import NotifyAdminAPIClient, cache


class EmailBrandingClient(NotifyAdminAPIClient):

    def __init__(self):
        super().__init__("a" * 73, "b")

    @cache.set('email_branding-{branding_id}')
    def get_email_branding(self, branding_id):
        return self.get(url='/email-branding/{}'.format(branding_id))

    @cache.set('email_branding')
    def get_all_email_branding(self, sort_key=None):
        brandings = self.get(url='/email-branding')['email_branding']
        if sort_key and sort_key in brandings[0]:
            brandings.sort(key=lambda branding: branding[sort_key].lower())
        return brandings

    def get_email_branding_id_for_domain(self, domain):
        for branding in self.get_all_email_branding():
            if domain and branding.get('domain') == domain:
                return branding['id']
        return None

    @cache.delete('email_branding')
    def create_email_branding(self, logo, name, text, colour, domain, brand_type):
        data = {
            "logo": logo,
            "name": name,
            "text": text,
            "colour": colour,
            "domain": domain,
            "brand_type": brand_type
        }
        return self.post(url="/email-branding", data=data)

    @cache.delete('email_branding')
    @cache.delete('email_branding-{branding_id}')
    def update_email_branding(self, branding_id, logo, name, text, colour, domain, brand_type):
        data = {
            "logo": logo,
            "name": name,
            "text": text,
            "colour": colour,
            "domain": domain,
            "brand_type": brand_type
        }
        return self.post(url="/email-branding/{}".format(branding_id), data=data)


email_branding_client = EmailBrandingClient()
