import eventlet
eventlet.monkey_patch()

from flask import Flask
from app import create_app

application = Flask('app')

create_app(application)
