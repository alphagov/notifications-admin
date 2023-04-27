from flask_login import current_user

from app.notify_client import NotifyAdminAPIClient, cache


class LetterAttachmentClient(NotifyAdminAPIClient):
    def get_letter_attachment(self, letter_attachment_id):
        return self.get(url=f"/letter-attachment/{letter_attachment_id}")

    @cache.delete("service-{service_id}-templates")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def create_letter_attachment(self, *, upload_id, original_filename, page_count, template_id, service_id):
        data = {
            "upload_id": str(upload_id),
            "original_filename": original_filename,
            "page_count": page_count,
            "template_id": str(template_id),
            "created_by_id": str(current_user.id),
        }
        return self.post(url="/letter-attachment", data=data)


letter_attachment_client = LetterAttachmentClient()
