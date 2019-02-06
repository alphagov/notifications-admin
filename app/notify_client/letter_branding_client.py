from app.notify_client import NotifyAdminAPIClient, cache


class LetterBrandingClient(NotifyAdminAPIClient):

    @cache.set('letter_branding-{branding_id}')
    def get_letter_branding(self, branding_id):
        return self.get(url='/letter-branding/{}'.format(branding_id))

    @cache.set('letter_branding')
    def get_all_letter_branding(self):
        return self.get(url='/letter-branding')

    @cache.delete('letter_branding')
    def create_letter_branding(self, filename, name, domain):
        data = {
            "filename": filename,
            "name": name,
            "domain": domain,
        }
        return self.post(url="/letter-branding", data=data)


letter_branding_client = LetterBrandingClient()
