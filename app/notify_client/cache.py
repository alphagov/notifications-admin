import json
from contextlib import suppress
from datetime import timedelta
from functools import wraps
from inspect import signature

from app.extensions import redis_client

TTL = int(timedelta(days=7).total_seconds())


def _get_argument(argument_name, client_method, args, kwargs):

    with suppress(KeyError):
        return kwargs[argument_name]

    with suppress(ValueError, IndexError):
        argument_index = list(signature(client_method).parameters).index(argument_name)
        return args[argument_index - 1]  # -1 because `args` doesn’t include `self`

    with suppress(KeyError):
        return signature(client_method).parameters[argument_name].default

    raise TypeError("{}() takes no argument called '{}'".format(
        client_method.__name__, argument_name
    ))


def _make_key(key_format, client_method, args, kwargs):
    return key_format.format(**{
        argument_name: _get_argument(argument_name, client_method, args, kwargs)
        for argument_name in list(signature(client_method).parameters)
    })


def set(key_format):

    def _set(client_method):

        @wraps(client_method)
        def new_client_method(client_instance, *args, **kwargs):
            redis_key = _make_key(key_format, client_method, args, kwargs)
            cached = redis_client.get(redis_key)
            if cached:
                return json.loads(cached.decode('utf-8'))
            api_response = client_method(client_instance, *args, **kwargs)
            redis_client.set(
                redis_key,
                json.dumps(api_response),
                ex=TTL,
            )
            return api_response

        return new_client_method
    return _set


def delete(key_format):

    def _delete(client_method):

        @wraps(client_method)
        def new_client_method(client_instance, *args, **kwargs):
            redis_key = _make_key(key_format, client_method, args, kwargs)
            redis_client.delete(redis_key)
            return client_method(client_instance, *args, **kwargs)

        return new_client_method

    return _delete
