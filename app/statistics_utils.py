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


def get_failure_rate_for_job(job):
    if not job.get('notifications_delivered'):
        if job.get('notifications_failed'):
            return 1
        return 0
    return (
        job.get('notifications_failed', 0) /
        (job.get('notifications_failed', 0) + job.get('notifications_delivered', 0))
    )


def add_rate_to_jobs(jobs):
    return [dict(
        **job,
        failure_rate=(get_failure_rate_for_job(job)) * 100
    ) for job in jobs]
