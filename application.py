from flask import Flask
from app import create_app

app = Flask('app')

create_app(app)
