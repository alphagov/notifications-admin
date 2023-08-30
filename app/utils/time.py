from datetime import date, datetime

import pytz
from dateutil import parser
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime


def get_current_financial_year():
    now = utc_string_to_aware_gmt_datetime(datetime.utcnow())
    current_month = int(now.strftime("%-m"))
    current_year = int(now.strftime("%Y"))
    return current_year if current_month > 3 else current_year - 1


def percentage_through_current_financial_year():
    """Returns an integer representing how far through the current financial year as a percentage (0-100)"""
    financial_year_start_date = date(get_current_financial_year(), 4, 1)
    now = utc_string_to_aware_gmt_datetime(datetime.utcnow()).date()
    financial_year_end_date = date(get_current_financial_year() + 1, 3, 31)
    days_in_financial_year = (financial_year_end_date - financial_year_start_date).days
    days_since_start_of_financial_year = (now - financial_year_start_date).days
    return int(days_since_start_of_financial_year * 100 / days_in_financial_year)


def is_less_than_days_ago(date_from_db, number_of_days):
    return (datetime.utcnow().astimezone(pytz.utc) - parser.parse(date_from_db)).days < number_of_days
