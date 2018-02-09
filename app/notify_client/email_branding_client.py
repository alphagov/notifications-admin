from app.notify_client import NotifyAdminAPIClient


class EmailBrandingClient(NotifyAdminAPIClient):

    def __init__(self):
        super().__init__("a" * 73, "b")

    def get_email_branding(self, branding_id):
        return self.get(url='/email-branding/{}'.format(branding_id))

    def get_all_email_branding(self):
        return self.get(url='/email-branding')['email_branding']

    def get_letter_email_branding(self):
        return self.get(url='/dvla_organisations')

    def create_email_branding(self, logo, name, colour):
        data = {
            "logo": logo,
            "name": name,
            "colour": colour
        }
        return self.post(url="/email-branding", data=data)

    def update_email_branding(self, branding_id, logo, name, colour):
        data = {
            "logo": logo,
            "name": name,
            "colour": colour
        }
        return self.post(url="/email-branding/{}".format(branding_id), data=data)
