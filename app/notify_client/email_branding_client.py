from app.notify_client import NotifyAdminAPIClient


class EmailBrandingClient(NotifyAdminAPIClient):

    def __init__(self):
        super().__init__("a" * 73, "b")

    def get_email_branding(self, branding_id):
        return self.get(url='/email-branding/{}'.format(branding_id))

    def get_all_email_branding(self, sort_key=None):
        brandings = self.get(url='/email-branding')['email_branding']
        if sort_key and sort_key in brandings[0]:
            brandings.sort(key=lambda branding: branding[sort_key].lower())
        return brandings

    def get_letter_email_branding(self):
        return self.get(url='/dvla_organisations')

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
