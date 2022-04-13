import json
import os

import pytest

from app.cloudfoundry_config import extract_cloudfoundry_config


@pytest.fixture
def vcap_services():
    return {
        'redis': [{
            'credentials': {
                'uri': 'redis uri'
            }
        }],
    }


def test_extract_cloudfoundry_config_populates_other_vars(os_environ, vcap_services):
    os.environ['VCAP_SERVICES'] = json.dumps(vcap_services)
    extract_cloudfoundry_config()

    assert os.environ['REDIS_URL'] == 'redis uri'


def test_extract_cloudfoundry_config_copes_if_redis_not_set(os_environ, vcap_services):
    del vcap_services['redis']
    os.environ['VCAP_SERVICES'] = json.dumps(vcap_services)

    extract_cloudfoundry_config()
    assert 'REDIS_URL' not in os.environ
