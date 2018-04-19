import json
from contextlib import suppress
from datetime import timedelta
from functools import wraps
from inspect import signature

TTL = int(timedelta(hours=24).total_seconds())


def _get_argument(argument_name, args, kwargs, client_method):

    with suppress(KeyError):
        return kwargs[argument_name]

    with suppress(ValueError, IndexError):
        return args[list(signature(client_method).parameters).index(argument_name) - 1]

    with suppress(KeyError):
        return signature(client_method).parameters[argument_name].default

    raise TypeError("{}() takes no argument called '{}'".format(
        client_method.__name__, argument_name
    ))


def list_of_strings(list_of_stuff):
    return list(map(str, filter(None, list_of_stuff)))


def _make_key(prefix, key_from_args, local_variables):
    return '-'.join(
        [
            local_variables['prefix']
        ] + list_of_strings(
            _get_argument(
                argument_name,
                local_variables['args'],
                local_variables['kwargs'],
                local_variables['client_method']
            ) for argument_name in key_from_args
        )
    )


def set(prefix, *key_from_args):

    def _set(client_method):

        @wraps(client_method)
        def new_client_method(client_instance, *args, **kwargs):
            redis_key = _make_key(prefix, key_from_args, locals())
            cached = client_instance.redis_client.get(redis_key)
            if cached:
                return json.loads(cached.decode('utf-8'))
            api_response = client_method(client_instance, *args, **kwargs)
            client_instance.redis_client.set(
                redis_key,
                json.dumps(api_response),
                ex=TTL,
            )
            return api_response

        return new_client_method
    return _set


def delete(prefix, *key_from_args):

    def _delete(client_method):

        @wraps(client_method)
        def new_client_method(client_instance, *args, **kwargs):
            redis_key = _make_key(prefix, key_from_args, locals())
            client_instance.redis_client.delete(redis_key)
            return client_method(client_instance, *args, **kwargs)

        return new_client_method

    return _delete
