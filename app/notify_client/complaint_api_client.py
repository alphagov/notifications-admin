from app.notify_client import NotifyAdminAPIClient


class ComplaintApiClient(NotifyAdminAPIClient):
    # Fudge assert in the super __init__ so
    # we can set those variables later.
    def __init__(self):
        super().__init__("a" * 73, "b")

    def get_all_complaints(self, page=1):
        params = {'page': page}
        return self.get('/complaint', params=params)

    def get_complaint_count(self, params_dict=None):
        return self.get('/complaint/count-by-date-range', params=params_dict)


complaint_api_client = ComplaintApiClient()
