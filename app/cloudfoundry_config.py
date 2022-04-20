import json
import os


def extract_cloudfoundry_config():
    vcap_services = json.loads(os.environ['VCAP_SERVICES'])
    os.environ['REDIS_URL'] = vcap_services['redis'][0]['credentials']['uri']
