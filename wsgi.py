from credstash import getAllSecrets
from whitenoise import WhiteNoise
import os

# On AWS get secrets and export to env, skip this on Cloud Foundry
if os.getenv('VCAP_SERVICES') is None:
    os.environ.update(getAllSecrets(region="eu-west-1"))

from app import create_app  # noqa

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'app', 'static')
STATIC_URL = 'static/'

application = WhiteNoise(create_app(), STATIC_ROOT, STATIC_URL)

if __name__ == "__main__":
        application.run()
