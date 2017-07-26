from app.notify_client import _attach_current_user, NotifyAdminAPIClient


class NotificationApiClient(NotifyAdminAPIClient):
    def __init__(self):
        super().__init__("a" * 73, "b")

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.api_key = '{}-{}'.format(
            app.config['ADMIN_CLIENT_USER_NAME'],
            app.config['ADMIN_CLIENT_SECRET'],
        )

    def get_notifications_for_service(
        self,
        service_id,
        job_id=None,
        template_type=None,
        status=None,
        page=None,
        page_size=None,
        limit_days=None,
        include_jobs=None,
        include_from_test_key=None,
        format_for_csv=None,
        to=None,
    ):
        params = {}
        if page is not None:
            params['page'] = page
        if page_size is not None:
            params['page_size'] = page_size
        if template_type is not None:
            params['template_type'] = template_type
        if status is not None:
            params['status'] = status
        if include_jobs is not None:
            params['include_jobs'] = include_jobs
        if include_from_test_key is not None:
            params['include_from_test_key'] = include_from_test_key
        if format_for_csv is not None:
            params['format_for_csv'] = format_for_csv
        if to is not None:
            params['to'] = to
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

    def send_notification(self, service_id, *, template_id, recipient, personalisation):
        data = {
            'template_id': template_id,
            'to': recipient,
            'personalisation': personalisation,
        }
        data = _attach_current_user(data)
        return self.post(url='/service/{}/send-notification'.format(service_id), data=data)

    def get_notification(self, service_id, notification_id):
        return self.get(url='/service/{}/notifications/{}'.format(service_id, notification_id))
