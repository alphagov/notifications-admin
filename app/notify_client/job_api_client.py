from collections import defaultdict

from app.notify_client import NotifyAdminAPIClient, _attach_current_user


class JobApiClient(NotifyAdminAPIClient):

    JOB_STATUSES = {
        'scheduled',
        'pending',
        'in progress',
        'finished',
        'cancelled',
        'sending limits exceeded',
        'ready to send',
        'sent to dvla'
    }

    def __init__(self):
        super().__init__("a" * 73, "b")

    @staticmethod
    def __convert_statistics(job):
        results = defaultdict(int)
        for outcome in job['statistics']:
            if outcome['status'] in ['failed', 'technical-failure', 'temporary-failure', 'permanent-failure']:
                results['failed'] += outcome['count']
            if outcome['status'] in ['sending', 'pending', 'created']:
                results['sending'] += outcome['count']
            if outcome['status'] in ['delivered', 'sent']:
                results['delivered'] += outcome['count']
            results['requested'] += outcome['count']
        return results

    def get_job(self, service_id, job_id):
        params = {}
        job = self.get(url='/service/{}/job/{}'.format(service_id, job_id), params=params)
        stats = self.__convert_statistics(job['data'])
        job['data']['notifications_sent'] = stats['delivered'] + stats['failed']
        job['data']['notifications_delivered'] = stats['delivered']
        job['data']['notifications_failed'] = stats['failed']
        job['data']['notifications_requested'] = stats['requested']

        return job

    def get_jobs(self, service_id, limit_days=None, statuses=None, page=1):
        params = {'page': page}
        if limit_days is not None:
            params['limit_days'] = limit_days
        if statuses is not None:
            params['statuses'] = ','.join(statuses)

        jobs = self.get(url='/service/{}/job'.format(service_id), params=params)
        for job in jobs['data']:
            stats = self.__convert_statistics(job)
            job['notifications_sent'] = stats['delivered'] + stats['failed']
            job['notifications_delivered'] = stats['delivered']
            job['notifications_failed'] = stats['failed']
            job['notifications_requested'] = stats['requested']

        return jobs

    def create_job(self, job_id, service_id, scheduled_for=None):

        data = {"id": job_id}

        if scheduled_for:
            data.update({'scheduled_for': scheduled_for})

        data = _attach_current_user(data)
        job = self.post(url='/service/{}/job'.format(service_id), data=data)

        stats = self.__convert_statistics(job['data'])
        job['data']['notifications_sent'] = stats['delivered'] + stats['failed']
        job['data']['notifications_delivered'] = stats['delivered']
        job['data']['notifications_failed'] = stats['failed']
        job['data']['notifications_requested'] = stats['requested']

        return job

    def cancel_job(self, service_id, job_id):

        job = self.post(
            url='/service/{}/job/{}/cancel'.format(service_id, job_id),
            data={}
        )

        stats = self.__convert_statistics(job['data'])
        job['data']['notifications_sent'] = stats['delivered'] + stats['failed']
        job['data']['notifications_delivered'] = stats['delivered']
        job['data']['notifications_failed'] = stats['failed']
        job['data']['notifications_requested'] = stats['requested']

        return job
