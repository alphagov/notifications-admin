from datetime import datetime

import pytz
from dateutil import parser
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime


def get_current_financial_year():
    now = utc_string_to_aware_gmt_datetime(
        datetime.utcnow()
    )
    current_month = int(now.strftime('%-m'))
    current_year = int(now.strftime('%Y'))
    return current_year if current_month > 3 else current_year - 1


def is_less_than_days_ago(date_from_db, number_of_days):
    return (
        datetime.utcnow().astimezone(pytz.utc) - parser.parse(date_from_db)
    ).days < number_of_days
