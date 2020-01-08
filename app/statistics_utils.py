from datetime import datetime
from functools import reduce

from dateutil import parser


def sum_of_statistics(delivery_statistics):

    statistics_keys = (
        'emails_delivered',
        'emails_requested',
        'emails_failed',
        'sms_requested',
        'sms_delivered',
        'sms_failed'
    )

    if not delivery_statistics or not delivery_statistics[0]:
        return {
            key: 0 for key in statistics_keys
        }

    return reduce(
        lambda x, y: {
            key: x.get(key, 0) + y.get(key, 0)
            for key in statistics_keys
        },
        delivery_statistics
    )


def add_rates_to(delivery_statistics):

    return dict(
        emails_failure_rate=get_formatted_percentage(
            delivery_statistics['emails_failed'],
            delivery_statistics['emails_requested']),
        sms_failure_rate=get_formatted_percentage(
            delivery_statistics['sms_failed'],
            delivery_statistics['sms_requested']),
        week_end_datetime=parser.parse(
            delivery_statistics.get('week_end', str(datetime.utcnow()))
        ),
        **delivery_statistics
    )


def get_formatted_percentage(x, tot):
    """
    Return a percentage to one decimal place (respecting )
    """
    return "{0:.1f}".format((float(x) / tot * 100)) if tot else '0'


def get_formatted_percentage_two_dp(x, tot):
    """
    Return a percentage to two decimal places
    """
    return "{0:.2f}".format((float(x) / tot * 100)) if tot else '0'


def statistics_by_state(statistics):
    return {
        'sms': {
            'processed': statistics['sms_requested'],
            'sending': (
                statistics['sms_requested'] - statistics['sms_failed'] - statistics['sms_delivered']
            ),
            'delivered': statistics['sms_delivered'],
            'failed': statistics['sms_failed']
        },
        'email': {
            'processed': statistics['emails_requested'],
            'sending': (
                statistics['emails_requested'] - statistics['emails_failed'] - statistics['emails_delivered']
            ),
            'delivered': statistics['emails_delivered'],
            'failed': statistics['emails_failed']
        }
    }
