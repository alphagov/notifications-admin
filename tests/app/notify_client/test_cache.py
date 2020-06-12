import pytest

from app.notify_client import cache


@pytest.mark.parametrize('args, kwargs, expected_cache_key', (
    (
        [1, 2, 3], {}, '1-2-3-None-None-None'
    ),
    (
        [1, 2, 3, 4, 5, 6], {}, '1-2-3-4-5-6'
    ),
    (
        [1, 2, 3], {'x': 4, 'y': 5, 'z': 6}, '1-2-3-4-5-6'
    ),
    (
        [1, 2, 3, 4], {'y': 5}, '1-2-3-4-5-None'
    ),
))
def test_sets_cache(
    mocker,
    args,
    kwargs,
    expected_cache_key,
):
    mock_redis_set = mocker.patch(
        'app.extensions.RedisClient.set',
    )
    mock_redis_get = mocker.patch(
        'app.extensions.RedisClient.get',
        return_value=None,
    )

    @cache.set('{a}-{b}-{c}-{x}-{y}-{z}')
    def foo(a, b, c, x=None, y=None, z=None):
        return 'bar'

    assert foo(*args, **kwargs) == 'bar'

    mock_redis_get.assert_called_once_with(expected_cache_key)

    mock_redis_set.assert_called_once_with(
        expected_cache_key,
        '"bar"',
        ex=604_800,
    )


def test_raises_if_key_doesnt_match_arguments():

    @cache.set('{baz}')
    def foo(bar):
        pass

    with pytest.raises(KeyError):
        foo(1)

    with pytest.raises(KeyError):
        foo()


def test_gets_from_cache(mocker):
    mock_redis_get = mocker.patch(
        'app.extensions.RedisClient.get',
        return_value=b'"bar"',
    )

    @cache.set('{a}-{b}-{c}')
    def foo(a, b, c):
        # This function should not be called because the cache has
        # returned a value
        raise RuntimeError

    assert foo(1, 2, 3) == 'bar'

    mock_redis_get.assert_called_once_with('1-2-3')


def test_deletes_from_cache(mocker):
    mock_redis_delete = mocker.patch(
        'app.extensions.RedisClient.delete'
    )

    @cache.delete('{a}-{b}-{c}')
    def foo(a, b, c):
        return 'bar'

    assert foo(1, 2, 3) == 'bar'

    mock_redis_delete.assert_called_once_with('1-2-3')


def test_deletes_from_cache_even_if_call_raises(mocker):
    mock_redis_delete = mocker.patch(
        'app.extensions.RedisClient.delete'
    )

    @cache.delete('bar')
    def foo():
        raise RuntimeError

    with pytest.raises(RuntimeError):
        foo()

    mock_redis_delete.assert_called_once_with('bar')
