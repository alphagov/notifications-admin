from app.notify_client import NotifyAdminAPIClient


class PerformanceDashboardAPIClient(NotifyAdminAPIClient):

    def get_performance_dashboard_stats(
        self,
        *,
        start_date,
        end_date,
    ):
        return self.get(
            '/performance-dashboard',
            params={
                'start_date': str(start_date),
                'end_date': str(end_date),
            }
        )


performance_dashboard_api_client = PerformanceDashboardAPIClient()
