import json
import os

import pytest

from app.cloudfoundry_config import extract_cloudfoundry_config


@pytest.fixture
def cloudfoundry_config():
    return {
        'redis': [{
            'credentials': {
                'uri': 'redis uri'
            }
        }],
    }


@pytest.fixture
def vcap_application(os_environ):
    os.environ['VCAP_APPLICATION'] = '{"space_name":"🚀🌌"}'


def test_extract_cloudfoundry_config_populates_other_vars(vcap_application, cloudfoundry_config):
    os.environ['VCAP_SERVICES'] = json.dumps(cloudfoundry_config)
    extract_cloudfoundry_config()

    assert os.environ['REDIS_URL'] == 'redis uri'
    assert os.environ['NOTIFY_ENVIRONMENT'] == '🚀🌌'
    assert os.environ['NOTIFY_LOG_PATH'] == '/home/vcap/logs/app.log'


def test_set_config_env_vars_copes_if_redis_not_set(vcap_application, cloudfoundry_config):
    del cloudfoundry_config['redis']
    os.environ['VCAP_SERVICES'] = json.dumps(cloudfoundry_config)

    extract_cloudfoundry_config()
    assert 'REDIS_URL' not in os.environ
