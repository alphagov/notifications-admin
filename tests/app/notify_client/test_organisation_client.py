from unittest.mock import call

import pytest

from app import organisations_client


@pytest.mark.parametrize(
    (
        'expected_cache_get_calls,'
        'cache_value,'
        'expected_api_calls,'
        'expected_cache_set_calls,'
        'expected_return_value,'
    ),
    [
        (
            [
                call('domains')
            ],
            b"""
                [
                    {"domains": ["a", "b", "c"]},
                    {"domains": ["c", "d", "e"]}
                ]
            """,
            [],
            [],
            ['a', 'b', 'c', 'd', 'e'],
        ),
        (
            [
                call('domains')
            ],
            None,
            [
                call(url='/organisations')
            ],
            [
                call(
                    'domains',
                    '["x", "y", "z"]',
                    ex=604800
                )
            ],
            'from api',
        ),
    ]
)
def test_returns_value_from_cache(
    app_,
    mocker,
    expected_cache_get_calls,
    cache_value,
    expected_return_value,
    expected_api_calls,
    expected_cache_set_calls,
):

    mock_redis_get = mocker.patch(
        'app.extensions.RedisClient.get',
        return_value=cache_value,
    )
    mock_api_get = mocker.patch(
        'app.notify_client.NotifyAdminAPIClient.get',
        return_value=[
            {'domains': ['x', 'y', 'z']}
        ],
    )
    mock_redis_set = mocker.patch(
        'app.extensions.RedisClient.set',
    )

    organisations_client.get_domains()

    assert mock_redis_get.call_args_list == expected_cache_get_calls
    assert mock_api_get.call_args_list == expected_api_calls
    assert mock_redis_set.call_args_list == expected_cache_set_calls


def test_deletes_domain_cache(
    app_,
    mock_get_user,
    mocker,
    fake_uuid,
):
    mocker.patch('app.notify_client.current_user', id='1')
    mock_redis_delete = mocker.patch('app.extensions.RedisClient.delete')
    mock_request = mocker.patch('notifications_python_client.base.BaseAPIClient.request')

    organisations_client.update_organisation(fake_uuid, foo='bar')

    assert call('domains') in mock_redis_delete.call_args_list
    assert len(mock_request.call_args_list) == 1
