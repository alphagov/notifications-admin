from app.notify_client import NotifyAdminAPIClient


class PlatformStatsAPIClient(NotifyAdminAPIClient):

    def get_aggregate_platform_stats(self, params_dict=None):
        return self.get("/platform-stats", params=params_dict)


platform_stats_api_client = PlatformStatsAPIClient()
