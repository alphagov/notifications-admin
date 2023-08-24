from app import Service, billing_api_client
from app.utils.time import get_current_financial_year, percentage_through_current_financial_year


def service_has_or_is_expected_to_send_x_or_more_notifications(service: Service, num_notifications):
    if sum(v or 0 for v in service.volumes_by_channel.values()) >= num_notifications:
        return True

    usage_last_year = sum(
        usage["notifications_sent"]
        for usage in billing_api_client.get_annual_usage_for_service(service.id, year=get_current_financial_year() - 1)
    )
    if usage_last_year >= num_notifications:
        return True

    usage_this_year = sum(
        usage["notifications_sent"]
        for usage in billing_api_client.get_annual_usage_for_service(service.id, year=get_current_financial_year())
    )
    estimated_usage_this_year = usage_this_year * (100 / percentage_through_current_financial_year())
    if estimated_usage_this_year >= num_notifications:
        return True

    return False
