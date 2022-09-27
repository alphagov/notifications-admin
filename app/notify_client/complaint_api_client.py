from app.notify_client import NotifyAdminAPIClient


class ComplaintApiClient(NotifyAdminAPIClient):
    def get_all_complaints(self, page=1):
        params = {"page": page}
        return self.get("/complaint", params=params)

    def get_complaint_count(self, params_dict=None):
        return self.get("/complaint/count-by-date-range", params=params_dict)


complaint_api_client = ComplaintApiClient()
