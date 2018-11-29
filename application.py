import os

from flask import Flask
from whitenoise import WhiteNoise

from app import create_app

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'app', 'static')
STATIC_URL = 'static/'

app = Flask('app')

create_app(app)
app.wsgi_app = WhiteNoise(app.wsgi_app, STATIC_ROOT, STATIC_URL)
