from notifications_python_client.base import BaseAPIClient


class StatisticsApiClient(BaseAPIClient):
    def __init__(self, base_url=None, client_id=None, secret=None):
        super(self.__class__, self).__init__(base_url=base_url or 'base_url',
                                             client_id=client_id or 'client_id',
                                             secret=secret or 'secret')

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.client_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.secret = app.config['ADMIN_CLIENT_SECRET']

    def get_statistics_for_service(self, service_id, limit_days=None):
        params = {}
        if limit_days is not None:
            params['limit_days'] = limit_days
        return self.get(
            url='/service/{}/notifications-statistics'.format(service_id),
            params=params
        )
