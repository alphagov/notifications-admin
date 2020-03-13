from app.notify_client import NotifyAdminAPIClient, _attach_current_user


class ContactListApiClient(NotifyAdminAPIClient):

    def create_contact_list(
        self,
        *,
        service_id,
        upload_id,
        original_file_name,
        row_count,
        template_type,
    ):
        data = {
            "id": upload_id,
            "original_file_name": original_file_name,
            "row_count": row_count,
            "template_type": template_type,
        }

        data = _attach_current_user(data)
        job = self.post(url='/service/{}/contact-list'.format(service_id), data=data)

        return job

    def get_contact_lists(self, service_id):
        return self.get('/service/{}/contact-list'.format(service_id))


contact_list_api_client = ContactListApiClient()
