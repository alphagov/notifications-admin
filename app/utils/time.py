from datetime import datetime

import pytz
from dateutil import parser
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime


def get_current_financial_year():
    now = utc_string_to_aware_gmt_datetime(datetime.utcnow())
    current_month = int(now.strftime("%-m"))
    current_year = int(now.strftime("%Y"))
    return current_year if current_month > 3 else current_year - 1


def percentage_through_current_financial_year():
    """Returns a float representing how far through the current financial year as a percentage (0.001-100)"""
    financial_year_start_date = utc_string_to_aware_gmt_datetime(datetime(get_current_financial_year(), 4, 1))
    now = utc_string_to_aware_gmt_datetime(datetime.utcnow())
    financial_year_end_date = utc_string_to_aware_gmt_datetime(datetime(get_current_financial_year() + 1, 3, 31))
    seconds_in_financial_year = (financial_year_end_date - financial_year_start_date).total_seconds()
    seconds_since_start_of_financial_year = (now - financial_year_start_date).total_seconds()
    percentage = round(seconds_since_start_of_financial_year * 100 / seconds_in_financial_year, 3)
    return max(0.001, min(100, percentage))


def is_less_than_days_ago(date_from_db, number_of_days):
    return (datetime.utcnow().astimezone(pytz.utc) - parser.parse(date_from_db)).days < number_of_days


def to_utc_string(aware_datetime):
    # Format matches app.utils.DATETIME_FORMAT in the API codebase
    return aware_datetime.astimezone(pytz.utc).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
