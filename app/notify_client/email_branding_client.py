from app.notify_client import NotifyAdminAPIClient, cache


class EmailBrandingClient(NotifyAdminAPIClient):
    @cache.set("email_branding-{branding_id}")
    def get_email_branding(self, branding_id):
        return self.get(url="/email-branding/{}".format(branding_id))

    @cache.set("email_branding")
    def get_all_email_branding(self):
        return self.get(url="/email-branding")["email_branding"]

    def get_email_branding_name_for_alt_text(self, alt_text):
        # a post rather than a get so we dont have to worry about URL/query param encoding for what could be
        # a relatively long and arbitrary unicode string full of spaces etc.
        resp = self.post(url="/email-branding/get-name-for-alt-text", data={"alt_text": alt_text})
        return resp["name"]

    @cache.delete("email_branding")
    def create_email_branding(self, *, logo, name, alt_text, text, colour, brand_type, created_by_id: str):
        data = {
            "logo": logo or None,
            "name": name,
            "alt_text": alt_text or None,
            "text": text or None,
            "colour": colour or None,
            "brand_type": brand_type,
            "created_by": created_by_id,
        }
        return self.post(url="/email-branding", data=data)["data"]

    @cache.delete("email_branding")
    @cache.delete("email_branding-{branding_id}")
    def update_email_branding(self, *, branding_id, logo, name, alt_text, text, colour, brand_type, updated_by_id: str):
        data = {
            "logo": logo or None,
            "name": name,
            "alt_text": alt_text,
            "text": text or None,
            "colour": colour or None,
            "brand_type": brand_type,
            "updated_by": updated_by_id,
        }
        return self.post(url="/email-branding/{}".format(branding_id), data=data)


email_branding_client = EmailBrandingClient()
