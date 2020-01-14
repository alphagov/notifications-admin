import os

import pytest

from app.cloudfoundry_config import extract_cloudfoundry_config


@pytest.fixture
def cloudfoundry_environ(os_environ):
    os.environ['VCAP_APPLICATION'] = '{"space_name":"🚀🌌"}'


def test_extract_cloudfoundry_config_populates_other_vars(cloudfoundry_environ):
    extract_cloudfoundry_config()

    assert os.environ['NOTIFY_ENVIRONMENT'] == '🚀🌌'
    assert os.environ['NOTIFY_LOG_PATH'] == '/home/vcap/logs/app.log'
