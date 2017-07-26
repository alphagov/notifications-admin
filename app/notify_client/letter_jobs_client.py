from app.notify_client import NotifyAdminAPIClient


class LetterJobsClient(NotifyAdminAPIClient):

    def __init__(self):
        super().__init__("a" * 73, "b")

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.api_key = '{}-{}'.format(
            app.config['ADMIN_CLIENT_USER_NAME'],
            app.config['ADMIN_CLIENT_SECRET'],
        )

    def get_letter_jobs(self):
        return self.get(url='/letter-jobs')['data']

    def send_letter_jobs(self, job_ids):
        return self.post(
            url='/send-letter-jobs',
            data={"job_ids": job_ids}
        )['data']
