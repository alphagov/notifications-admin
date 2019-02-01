from app.notify_client import NotifyAdminAPIClient, cache


class LetterBrandingClient(NotifyAdminAPIClient):

    @cache.set('letter_branding-{branding_id}')
    def get_letter_branding(self, branding_id):
        return self.get(url='/letter-branding/{}'.format(branding_id))

    @cache.set('letter_branding')
    def get_all_letter_branding(self, sort_key=None):
        brandings = self.get(url='/letter-branding')
        if sort_key and sort_key in brandings[0]:
            brandings.sort(key=lambda branding: branding[sort_key].lower())
        return brandings

    @cache.delete('letter_branding')
    def create_letter_branding(self, filename, name, domain):
        data = {
            "filename": filename,
            "name": name,
            "domain": domain,
        }
        return self.post(url="/letter-branding", data=data)


letter_branding_client = LetterBrandingClient()
