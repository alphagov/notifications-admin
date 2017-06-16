from freezegun import freeze_time
import pytest
from werkzeug.datastructures import MultiDict

from app.main.views.notifications import get_status_arg
from app.utils import (
    REQUESTED_STATUSES,
    FAILURE_STATUSES,
    SENDING_STATUSES,
    DELIVERED_STATUSES,
)


@pytest.mark.parametrize('multidict_args, expected_statuses', [
    ([], REQUESTED_STATUSES),
    ([('status', '')], REQUESTED_STATUSES),
    ([('status', 'garbage')], REQUESTED_STATUSES),
    ([('status', 'sending')], SENDING_STATUSES),
    ([('status', 'delivered')], DELIVERED_STATUSES),
    ([('status', 'failed')], FAILURE_STATUSES),
])
def test_status_filters(mocker, multidict_args, expected_statuses):
    mocker.patch('app.main.views.notifications.current_app')

    args = MultiDict(multidict_args)
    args['status'] = get_status_arg(args)

    assert sorted(args['status']) == sorted(expected_statuses)
