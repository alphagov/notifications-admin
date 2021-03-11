import random
import uuid
from datetime import date

from freezegun import freeze_time

from tests.conftest import normalize_spaces


def _get_example_performance_data():
    return {
      "total_notifications": 1_789_000_000,
      "email_notifications": 1_123_000_000,
      "sms_notifications": 987_654_321,
      "letter_notifications": 1_234_567,
      "live_service_count": random.randrange(1, 1000),
      "notifications_by_type": [
        {
          "date": "2021-02-21",
          "emails": 1_234_567, "sms": 123_456, "letters": 123,
        },
        {
          "date": "2021-02-22",
          "emails": 1, "sms": 2, "letters": 3,
        },
        {
          "date": "2021-02-23",
          "emails": 1, "sms": 2, "letters": 3,
        },
        {
          "date": "2021-02-24",
          "emails": 1, "sms": 2, "letters": 3,
        },
        {
          "date": "2021-02-25",
          "emails": 1, "sms": 2, "letters": 3,
        },
        {
          "date": "2021-02-26",
          "emails": 1, "sms": 2, "letters": 3,
        },
        {
          "date": "2021-02-27",
          "emails": 1, "sms": 2, "letters": 3,
        },
      ],
      "processing_time": [
        {
          "date": "2021-02-21",
          "percentage_under_10_seconds": 99.2
        },
        {
          "date": "2021-02-22",
          "percentage_under_10_seconds": 95.3
        },
        {
          "date": "2021-02-23",
          "percentage_under_10_seconds": 95.6
        },
        {
          "date": "2021-02-24",
          "percentage_under_10_seconds": 96.7
        },
        {
          "date": "2021-02-25",
          "percentage_under_10_seconds": 95.7
        },
        {
          "date": "2021-02-26",
          "percentage_under_10_seconds": 96.5
        },
        {
          "date": "2021-02-27",
          "percentage_under_10_seconds": 98.6
        },
      ],
      "services_using_notify": [
        {
          "organisation_id": uuid.uuid4(),
          "organisation_name": "Department of Examples and Patterns",
          "service_id": uuid.uuid4(),
          "service_name": "Example service"
        },
        {
          "organisation_id": uuid.uuid4(),
          "organisation_name": "Department of Examples and Patterns",
          "service_id": uuid.uuid4(),
          "service_name": "Example service 2"
        },
        {
          "organisation_id": uuid.uuid4(),
          "organisation_name": "Department of One Service",
          "service_id": uuid.uuid4(),
          "service_name": "Example service 3"
        },
      ],
    }


@freeze_time('2021-01-01')
def test_should_render_performance_page(
    mocker,
    client_request,
    mock_get_service_and_organisation_counts,
):
    mock_get_performance_data = mocker.patch(
        'app.performance_dashboard_api_client.get_performance_dashboard_stats',
        return_value=_get_example_performance_data(),
    )
    page = client_request.get('main.performance')
    mock_get_performance_data.assert_called_once_with(
        start_date=date(2020, 12, 25),
        end_date=date(2021, 1, 1),
    )
    assert normalize_spaces(page.select_one('main').text) == (
        'Performance data '
        ''
        'Messages sent since May 2016 '
        'Total messages '
        '1.8 billion total '
        '1.1 billion emails '
        '987.7 million text messages '
        '1.2 million letters '
        ''
        'Date Emails Text messages Letters '
        '21 February 2021 1,234,567 123,456 123 '
        '22 February 2021 1 2 3 '
        '23 February 2021 1 2 3 '
        '24 February 2021 1 2 3 '
        '25 February 2021 1 2 3 '
        '26 February 2021 1 2 3 '
        '27 February 2021 1 2 3 '
        'Only showing the last 7 days '
        ''
        'Messages sent within 10 seconds '
        'Average '
        '96.8% on average '
        'Date Percentage '
        '27 February 2021 98.6% '
        '26 February 2021 96.5% '
        '25 February 2021 95.7% '
        '24 February 2021 96.7% '
        '23 February 2021 95.6% '
        '22 February 2021 95.3% '
        '21 February 2021 99.2% '
        'Only showing the last 7 days '
        ''
        'Organisations using Notify '
        'Organisations 111 organisations '
        'Services 9,999 services '
        'Organisation Number of live services '
        'Department of Examples and Patterns 2 '
        'Department of One Service 1'
    )
