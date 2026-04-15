from itertools import count, islice

import pytest

from app.utils.interruptible_io import InterruptibleIter


def test_interruptible_iter_single(mocker):
    mock_sleep = mocker.patch("app.utils.interruptible_io.sleep")
    i = InterruptibleIter(islice(count(), 0, 9), interruptible_every=3)

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


def test_interruptible_iter_synced(mocker):
    mock_sleep = mocker.patch("app.utils.interruptible_io.sleep")
    i = InterruptibleIter(islice(count(), 0, 6), interruptible_every=3)
    j = InterruptibleIter("abcdefghij", sync_with=i)

    assert next(i) == 0
    assert len(mock_sleep.mock_calls) == 0
    assert next(j) == "a"
    assert len(mock_sleep.mock_calls) == 0
    assert next(j) == "b"
    assert len(mock_sleep.mock_calls) == 0
    assert next(i) == 1
    assert len(mock_sleep.mock_calls) == 1
    assert next(i) == 2
    assert len(mock_sleep.mock_calls) == 1
    assert next(i) == 3
    assert len(mock_sleep.mock_calls) == 1
    assert next(j) == "c"
    assert len(mock_sleep.mock_calls) == 2
    assert next(i) == 4
    assert len(mock_sleep.mock_calls) == 2
    assert next(i) == 5
    assert len(mock_sleep.mock_calls) == 2

    with pytest.raises(StopIteration):
        next(i)

    assert len(mock_sleep.mock_calls) == 2

    assert next(j) == "d"
    assert len(mock_sleep.mock_calls) == 3
    assert next(j) == "e"
    assert len(mock_sleep.mock_calls) == 3
    assert next(j) == "f"
    assert len(mock_sleep.mock_calls) == 3
    assert next(j) == "g"
    assert len(mock_sleep.mock_calls) == 4
    assert next(j) == "h"
    assert len(mock_sleep.mock_calls) == 4
    assert next(j) == "i"
    assert len(mock_sleep.mock_calls) == 4
    assert next(j) == "j"
    assert len(mock_sleep.mock_calls) == 5

    with pytest.raises(StopIteration):
        next(j)

    assert len(mock_sleep.mock_calls) == 5
