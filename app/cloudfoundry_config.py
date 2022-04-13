import json
import os


def extract_cloudfoundry_config():
    vcap_services = json.loads(os.environ['VCAP_SERVICES'])

    # Redis config
    if 'redis' in vcap_services:
        os.environ['REDIS_URL'] = vcap_services['redis'][0]['credentials']['uri']
