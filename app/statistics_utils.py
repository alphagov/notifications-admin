from datetime import datetime
from dateutil import parser
from functools import reduce


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
        emails_failure_rate=(
            "{0:.1f}".format(
                float(delivery_statistics['emails_failed']) / delivery_statistics['emails_requested'] * 100
            )
            if delivery_statistics['emails_requested'] else 0
        ),
        sms_failure_rate=(
            "{0:.1f}".format(
                float(delivery_statistics['sms_failed']) / delivery_statistics['sms_requested'] * 100
            )
            if delivery_statistics['sms_requested'] else 0
        ),
        week_end_datetime=parser.parse(
            delivery_statistics.get('week_end', str(datetime.utcnow()))
        ),
        **delivery_statistics
    )
