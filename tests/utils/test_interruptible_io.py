from itertools import count, islice

import pytest

from app.utils.interruptible_io import interruptible_iter


def test_interruptible_iter(mocker):
    mock_sleep = mocker.patch("app.utils.interruptible_io.sleep")
    i = interruptible_iter(islice(count(), 0, 9), 3)

    assert next(i) == 0
    assert len(mock_sleep.mock_calls) == 0
    assert next(i) == 1
    assert len(mock_sleep.mock_calls) == 0
    assert next(i) == 2
    assert len(mock_sleep.mock_calls) == 0
    assert next(i) == 3
    assert len(mock_sleep.mock_calls) == 1
    assert next(i) == 4
    assert len(mock_sleep.mock_calls) == 1
    assert next(i) == 5
    assert len(mock_sleep.mock_calls) == 1
    assert next(i) == 6
    assert len(mock_sleep.mock_calls) == 2
    assert next(i) == 7
    assert len(mock_sleep.mock_calls) == 2
    assert next(i) == 8
    assert len(mock_sleep.mock_calls) == 2

    with pytest.raises(StopIteration):
        next(i)

    assert len(mock_sleep.mock_calls) == 2
