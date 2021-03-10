from app.notify_client import NotifyAdminAPIClient


class PerformanceDashboardAPIClient(NotifyAdminAPIClient):

    def get_performance_dashboard_stats(self, params_dict=None):
        return self.get("/performance-dashboard", params=params_dict)


performance_dashboard_api_client = PerformanceDashboardAPIClient()
