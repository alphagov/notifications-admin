from app.notify_client import NotifyAdminAPIClient


class LetterJobsClient(NotifyAdminAPIClient):
    def submit_returned_letters(self, references):
        return self.post(url="/letters/returned", data={"references": references})


letter_jobs_client = LetterJobsClient()
