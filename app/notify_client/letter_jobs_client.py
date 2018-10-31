from app.notify_client import NotifyAdminAPIClient


class LetterJobsClient(NotifyAdminAPIClient):

    def __init__(self):
        super().__init__("a" * 73, "b")

    def get_letter_jobs(self):
        return self.get(url='/letter-jobs')['data']

    def send_letter_jobs(self, job_ids):
        return self.post(
            url='/send-letter-jobs',
            data={"job_ids": job_ids}
        )['data']

    def submit_returned_letters(self, references):
        return self.post(
            url='/letters/returned',
            data={'references': references}
        )


letter_jobs_client = LetterJobsClient()
