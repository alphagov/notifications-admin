import json
import os


def extract_cloudfoundry_config():
    vcap_services = json.loads(os.environ["VCAP_SERVICES"])
    # redis config
    if "REDIS_URL" not in os.environ:
        os.environ["REDIS_URL"] = vcap_services["redis"][0]["credentials"]["uri"]
