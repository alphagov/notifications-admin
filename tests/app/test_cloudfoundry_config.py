import os
import json

import pytest

from app.cloudfoundry_config import extract_cloudfoundry_config, set_config_env_vars


@pytest.fixture
def notify_config():
    return {
        'name': 'notify-config',
        'credentials': {
            'api_host_name': 'api host name',
            'admin_base_url': 'admin base url',
            'admin_client_secret': 'admin client secret',
            'secret_key': 'secret key',
            'dangerous_salt': 'dangerous salt',
        }
    }


@pytest.fixture
def aws_config():
    return {
        'name': 'notify-aws',
        'credentials': {
            'aws_access_key_id': 'aws access key id',
            'aws_secret_access_key': 'aws secret access key',
        }
    }


@pytest.fixture
def hosted_graphite_config():
    return {
        'name': 'hosted-graphite',
        'credentials': {
            'statsd_prefix': 'statsd prefix'
        }
    }


@pytest.fixture
def deskpro_config():
    return {
        'name': 'deskpro',
        'credentials': {
            'api_host': 'deskpro api host',
            'api_key': 'deskpro api key'
        }
    }


@pytest.fixture
def template_preview_config():
    return {
        'name': 'notify-template-preview',
        'credentials': {
            'api_host': 'template-preview api host',
            'api_key': 'template-preview api key'
        }
    }


@pytest.fixture
def cloudfoundry_config(
        notify_config,
        aws_config,
        hosted_graphite_config,
        deskpro_config,
        template_preview_config,
):
    return {
        'user-provided': [
            notify_config,
            aws_config,
            hosted_graphite_config,
            deskpro_config,
            template_preview_config,
        ]
    }


@pytest.fixture
def cloudfoundry_environ(monkeypatch, cloudfoundry_config):
    monkeypatch.setenv('VCAP_SERVICES', json.dumps(cloudfoundry_config))
    monkeypatch.setenv('VCAP_APPLICATION', '{"space_name":"🚀🌌"}')


@pytest.mark.usefixtures('os_environ', 'cloudfoundry_environ')
def test_extract_cloudfoundry_config_populates_other_vars():
    extract_cloudfoundry_config()

    assert os.environ['LOGGING_STDOUT_JSON'] == '1'
    assert os.environ['NOTIFY_ENVIRONMENT'] == '🚀🌌'


@pytest.mark.usefixtures('os_environ', 'cloudfoundry_environ')
def test_set_config_env_vars_ignores_unknown_configs(cloudfoundry_config):
    cloudfoundry_config['foo'] = {'credentials': {'foo': 'foo'}}
    cloudfoundry_config['user-provided'].append({
        'name': 'bar', 'credentials': {'bar': 'bar'}
    })

    set_config_env_vars(cloudfoundry_config)

    assert 'foo' not in os.environ
    assert 'bar' not in os.environ


@pytest.mark.usefixtures('os_environ', 'cloudfoundry_environ')
def test_notify_config():
    extract_cloudfoundry_config()

    assert os.environ['API_HOST_NAME'] == 'api host name'
    assert os.environ['ADMIN_BASE_URL'] == 'admin base url'
    assert os.environ['ADMIN_CLIENT_SECRET'] == 'admin client secret'
    assert os.environ['SECRET_KEY'] == 'secret key'
    assert os.environ['DANGEROUS_SALT'] == 'dangerous salt'


@pytest.mark.usefixtures('os_environ', 'cloudfoundry_environ')
def test_aws_config():
    extract_cloudfoundry_config()

    assert os.environ['AWS_ACCESS_KEY_ID'] == 'aws access key id'
    assert os.environ['AWS_SECRET_ACCESS_KEY'] == 'aws secret access key'


@pytest.mark.usefixtures('os_environ', 'cloudfoundry_environ')
def test_hosted_graphite_config():
    extract_cloudfoundry_config()

    assert os.environ['STATSD_PREFIX'] == 'statsd prefix'


@pytest.mark.usefixtures('os_environ', 'cloudfoundry_environ')
def test_deskpro_config():
    extract_cloudfoundry_config()

    assert os.environ['DESKPRO_API_HOST'] == 'deskpro api host'
    assert os.environ['DESKPRO_API_KEY'] == 'deskpro api key'


@pytest.mark.usefixtures('os_environ', 'cloudfoundry_environ')
def test_template_preview_config():
    extract_cloudfoundry_config()

    assert os.environ['TEMPLATE_PREVIEW_API_HOST'] == 'template-preview api host'
    assert os.environ['TEMPLATE_PREVIEW_API_KEY'] == 'template-preview api key'
