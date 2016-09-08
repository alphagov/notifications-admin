from notifications_python_client.base import BaseAPIClient


class NotificationApiClient(BaseAPIClient):
    def __init__(self, base_url=None, service_id=None, api_key=None):
        super(self.__class__, self).__init__(base_url=base_url or 'base_url',
                                             service_id=service_id or 'service_id',
                                             api_key=api_key or 'api_key')

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.service_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = app.config['ADMIN_CLIENT_SECRET']

    def get_all_notifications(self, page=None):
        params = {}
        if page is not None:
            params['page'] = page
        return self.get(
            url='/notifications',
            params=params
        )

    def get_notifications_for_service(self,
                                      service_id,
                                      job_id=None,
                                      template_type=None,
                                      status=None,
                                      page=None,
                                      page_size=None,
                                      limit_days=None):
        params = {}
        if page is not None:
            params['page'] = page
        if page_size is not None:
            params['page_size'] = page_size
        if template_type is not None:
            params['template_type'] = template_type
        if status is not None:
            params['status'] = status
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
