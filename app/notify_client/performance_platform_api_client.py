from app.notify_client import NotifyAdminAPIClient


class PerformancePlatformAPIClient(NotifyAdminAPIClient):

    def get_performance_platform_stats(self, params_dict=None):
        return self.get("/performance-platform", params=params_dict)


performance_platform_api_client = PerformancePlatformAPIClient()
