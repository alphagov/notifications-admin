from notifications_python_client.base import BaseAPIClient


class NotificationApiClient(BaseAPIClient):
    def __init__(self):
        super().__init__("a", "b", "c")

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.service_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = app.config['ADMIN_CLIENT_SECRET']

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
        include_from_test_key=None
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
