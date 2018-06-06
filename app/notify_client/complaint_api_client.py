from app.notify_client import NotifyAdminAPIClient


class ComplaintApiClient(NotifyAdminAPIClient):
    # Fudge assert in the super __init__ so
    # we can set those variables later.
    def __init__(self):
        super().__init__("a" * 73, "b")

    def get_all_complaints(self):
        return self.get('/complaint')
