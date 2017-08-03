from whitenoise import WhiteNoise
import os

from app import create_app  # noqa

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'app', 'static')
STATIC_URL = 'static/'

application = WhiteNoise(create_app(), STATIC_ROOT, STATIC_URL)

if __name__ == "__main__":
    application.run()
