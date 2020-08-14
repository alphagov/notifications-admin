"""
Extracts cloudfoundry config from its json and populates the environment variables that we would expect to be populated
on local/aws boxes
"""

import os
import json


def extract_cloudfoundry_config():
    vcap_services = json.loads(os.environ['VCAP_SERVICES'])
    vcap_application = json.loads(os.environ['VCAP_APPLICATION'])
    set_config_env_vars(vcap_services, vcap_application)


def set_config_env_vars(vcap_services, vcap_application):
    os.environ['REDIS_URL'] = vcap_services['redis'][0]['credentials']['uri']
    os.environ['NOTIFY_ENVIRONMENT'] = vcap_application['space_name']
    os.environ['NOTIFY_LOG_PATH'] = '/home/vcap/logs/app.log'
