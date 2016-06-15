import pytest

from app.statistics_utils import sum_of_statistics, add_rates_to, statistics_by_state


@pytest.mark.parametrize('delivery_statistics', [
    None,
    [{}],
    [{'emails_requested': 0}, {'emails_requested': 0}]
])
def test_sum_of_statistics_puts_in_defaults_of_zero(delivery_statistics):
    resp = sum_of_statistics(delivery_statistics)

    assert resp == {
        'emails_delivered': 0,
        'emails_requested': 0,
        'emails_failed': 0,
        'sms_requested': 0,
        'sms_delivered': 0,
        'sms_failed': 0
    }


def test_sum_of_statistics_sums_inputs():
    delivery_statistics = [
        {
            'emails_delivered': 1,
            'emails_requested': 2,
            'emails_failed': 3,
            'sms_requested': 4,
            'sms_delivered': 5,
            'sms_failed': 6
        },
        {
            'emails_delivered': 10,
            'emails_requested': 20,
            'emails_failed': 30,
            'sms_requested': 40,
            'sms_delivered': 50,
            'sms_failed': 60
        }
    ]
    resp = sum_of_statistics(delivery_statistics)

    assert resp == {
        'emails_delivered': 11,
        'emails_requested': 22,
        'emails_failed': 33,
        'sms_requested': 44,
        'sms_delivered': 55,
        'sms_failed': 66
    }


@pytest.mark.parametrize('emails_failed,emails_requested,expected_failure_rate', [
    (0, 0, 0),
    (0, 1, '0.0'),
    (1, 3, '33.3')
])
def test_add_rates_sets_email_failure_rate(emails_failed, emails_requested, expected_failure_rate):
    resp = add_rates_to({
        'emails_failed': emails_failed,
        'emails_requested': emails_requested,
        'sms_failed': 0,
        'sms_requested': 0
    })

    assert resp['emails_failure_rate'] == expected_failure_rate


@pytest.mark.parametrize('sms_failed,sms_requested,expected_failure_rate', [
    (0, 0, 0),
    (0, 1, '0.0'),
    (1, 3, '33.3')
])
def test_add_rates_sets_sms_failure_rate(sms_failed, sms_requested, expected_failure_rate):
    resp = add_rates_to({
        'emails_failed': 0,
        'emails_requested': 0,
        'sms_failed': sms_failed,
        'sms_requested': sms_requested
    })

    assert resp['sms_failure_rate'] == expected_failure_rate


def test_add_rates_keeps_original_raw_data():
    resp = add_rates_to({
        'emails_failed': 1,
        'emails_requested': 2,
        'sms_failed': 3,
        'sms_requested': 4
    })

    assert resp['emails_failed'] == 1
    assert resp['emails_requested'] == 2
    assert resp['sms_failed'] == 3
    assert resp['sms_requested'] == 4


def test_service_statistics_by_state():
    resp = statistics_by_state({
        'emails_requested': 3,
        'emails_failed': 1,
        'emails_delivered': 1,
        'sms_requested': 3,
        'sms_failed': 1,
        'sms_delivered': 1
    })

    for message_type in ['email', 'sms']:
        assert resp[message_type]['processed'] == 3
        assert resp[message_type]['sending'] == 1
        assert resp[message_type]['delivered'] == 1
        assert resp[message_type]['failed'] == 1
