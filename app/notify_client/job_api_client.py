
from notifications_python_client.base import BaseAPIClient
from app.notify_client import _attach_current_user


class JobApiClient(BaseAPIClient):
    def __init__(self, base_url=None, client_id=None, secret=None):
        super(self.__class__, self).__init__(base_url=base_url or 'base_url',
                                             client_id=client_id or 'client_id',
                                             secret=secret or 'secret')

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.client_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.secret = app.config['ADMIN_CLIENT_SECRET']

    def get_job(self, service_id, job_id=None, limit_days=None):
        if job_id:
            return self.get(url='/service/{}/job/{}'.format(service_id, job_id))
        params = {}
        if limit_days is not None:
            params['limit_days'] = limit_days
        return self.get(url='/service/{}/job'.format(service_id), params=params)

    def create_job(self, job_id, service_id, template_id, original_file_name, notification_count):
        data = {
            "id": job_id,
            "template": template_id,
            "original_file_name": original_file_name,
            "notification_count": notification_count
        }
        _attach_current_user(data)
        resp = self.post(url='/service/{}/job'.format(service_id), data=data)
        return resp['data']
