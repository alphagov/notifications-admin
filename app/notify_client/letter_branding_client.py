from app.notify_client import NotifyAdminAPIClient, cache


class LetterBrandingClient(NotifyAdminAPIClient):
    @cache.set("letter_branding-{branding_id}")
    def get_letter_branding(self, branding_id):
        return self.get(url="/letter-branding/{}".format(branding_id))

    @cache.set("letter_branding")
    def get_all_letter_branding(self):
        return self.get(url="/letter-branding")

    @cache.delete("letter_branding")
    def create_letter_branding(self, *, filename, name, created_by_id):
        data = {
            "filename": filename,
            "name": name,
            "created_by_id": created_by_id,
        }
        return self.post(url="/letter-branding", data=data)

    @cache.delete("letter_branding")
    @cache.delete("letter_branding-{branding_id}")
    @cache.delete_by_pattern("organisation-*-letter-branding-pool")
    def update_letter_branding(self, *, branding_id, filename, name, updated_by_id):
        data = {
            "filename": filename,
            "name": name,
            "updated_by_id": updated_by_id,
        }
        return self.post(url=f"/letter-branding/{branding_id}", data=data)


letter_branding_client = LetterBrandingClient()
