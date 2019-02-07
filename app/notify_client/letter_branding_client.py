from app.notify_client import NotifyAdminAPIClient


class LetterBrandingClient(NotifyAdminAPIClient):

    def get_letter_branding(self):
        return self.get(url='/dvla_organisations')

    def create_letter_branding(self, filename, name, domain):
        data = {
            "filename": filename,
            "name": name,
            "domain": domain,
        }
        return self.post(url="/letter-branding", data=data)


letter_branding_client = LetterBrandingClient()
