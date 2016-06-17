from notifications_python_client.base import BaseAPIClient
from notifications_python_client.errors import HTTPError


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

    def get_statistics_for_service_for_day(self, service_id, day):
        url = '/service/{}/notifications-statistics/day/{}'.format(service_id, day)
        try:
            self.get(url=url)['data']
        except HTTPError as e:
            if e.status_code == 404:
                return None

    def get_7_day_aggregate_for_service(self, service_id, date_from=None, week_count=None):
        params = {}
        if date_from is not None:
            params['date_from'] = date_from
        if week_count is not None:
            params['week_count'] = week_count
        return self.get(
            url='/service/{}/notifications-statistics/seven_day_aggregate'.format(service_id),
            params=params
        )

    def get_statistics_for_all_services_for_day(self, day):
        params = {
            'day': day
        }
        return self.get(url='/notifications/statistics', params=params)
