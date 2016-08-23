
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

    @staticmethod
    def __convert_statistics(job):
        results = {
            'sending': 0,
            'delivered': 0,
            'failed': 0
        }
        if 'statistics' in job:
            for outcome in job['statistics']:
                if outcome['status'] in ['failed', 'technical-failure', 'temporary-failure', 'permanent-failure']:
                    results['failed'] += outcome['count']
                if outcome['status'] in ['sending', 'pending', 'created']:
                    results['sending'] += outcome['count']
                if outcome['status'] in ['delivered']:
                    results['delivered'] += outcome['count']
        return results

    def get_job(self, service_id, job_id=None, limit_days=None, status=None):
        if job_id:
            params = {}
            if status is not None:
                params['status'] = status
            job = self.get(url='/service/{}/job/{}'.format(service_id, job_id), params=params)

            if 'notifications_sent' not in job['data']:
                stats = self.__convert_statistics(job)
                job['data']['notifications_sent'] = stats['sending']
                job['data']['notifications_delivered'] = stats['delivered']
                job['data']['notifications_failed'] = stats['failed']
            return job

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
        data = _attach_current_user(data)
        resp = self.post(url='/service/{}/job'.format(service_id), data=data)

        if 'notifications_sent' not in resp['data']:
            stats = self.__convert_statistics(resp)
            resp['data']['notifications_sent'] = stats['sending']
            resp['data']['notifications_delivered'] = stats['delivered']
            resp['data']['notifications_failed'] = stats['failed']

        return resp
