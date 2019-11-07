from app.notify_client import NotifyAdminAPIClient, _attach_current_user


class NotificationApiClient(NotifyAdminAPIClient):

    def get_notifications_for_service(
        self,
        service_id,
        job_id=None,
        template_type=None,
        status=None,
        page=None,
        page_size=None,
        count_pages=None,
        limit_days=None,
        include_jobs=None,
        include_from_test_key=None,
        format_for_csv=None,
        to=None,
        include_one_off=None,
    ):
        # TODO: if "to" is included, this should be a POST
        params = {
            'page': page,
            'page_size': page_size,
            'template_type': template_type,
            'status': status,
            'include_jobs': include_jobs,
            'include_from_test_key': include_from_test_key,
            'format_for_csv': format_for_csv,
            'to': to,
            'include_one_off': include_one_off,
            'count_pages': count_pages,
        }

        params = {k: v for k, v in params.items() if v is not None}

        if job_id:
            return self.get(
                url='/service/{}/job/{}/notifications'.format(service_id, job_id),
                params=params
            )
        else:
            if limit_days is not None:
                params['limit_days'] = limit_days
            return self.get(
                url='/service/{}/notifications'.format(service_id),
                params=params
            )

    def send_notification(self, service_id, *, template_id, recipient, personalisation, sender_id):
        data = {
            'template_id': template_id,
            'to': recipient,
            'personalisation': personalisation,
        }
        if sender_id:
            data['sender_id'] = sender_id
        data = _attach_current_user(data)
        return self.post(url='/service/{}/send-notification'.format(service_id), data=data)

    def send_precompiled_letter(self, service_id, filename, file_id, postage):
        data = {
            'filename': filename,
            'file_id': file_id,
            'postage': postage,
        }
        data = _attach_current_user(data)
        return self.post(url='/service/{}/send-pdf-letter'.format(service_id), data=data)

    def get_notification(self, service_id, notification_id):
        return self.get(url='/service/{}/notifications/{}'.format(service_id, notification_id))

    def get_api_notifications_for_service(self, service_id):
        ret = self.get_notifications_for_service(
            service_id,
            include_jobs=False,
            include_from_test_key=True,
            include_one_off=False,
            count_pages=False
        )
        return self.map_letters_to_accepted(ret)

    @staticmethod
    def map_letters_to_accepted(notifications):
        for notification in notifications['notifications']:
            if notification['notification_type'] == 'letter':
                if notification['status'] in ('created', 'sending'):
                    notification['status'] = 'accepted'

                if notification['status'] in ('delivered', 'returned-letter'):
                    notification['status'] = 'received'
        return notifications

    def get_notification_letter_preview(self, service_id, notification_id, file_type, page=None):

        get_url = '/service/{}/template/preview/{}/{}{}'.format(
            service_id,
            notification_id,
            file_type,
            '?page={}'.format(page) if page else ''
        )

        return self.get(url=get_url)

    def update_notification_to_cancelled(self, service_id, notification_id):
        return self.post(
            url='/service/{}/notifications/{}/cancel'.format(service_id, notification_id),
            data={})

    def get_notification_status_by_service(self, start_date, end_date):
        return self.get(
            url='service/monthly-data-by-service',
            params={
                'start_date': str(start_date),
                'end_date': str(end_date),
            }
        )

    def get_notification_count_for_job_id(self, *, service_id, job_id):
        return self.get(url='/service/{}/job/{}/notification_count'.format(service_id, job_id))["count"]


notification_api_client = NotificationApiClient()
