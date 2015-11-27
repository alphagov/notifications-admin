import hashlib
from flask import current_app


def encrypt(value):
    key = current_app.config['SECRET_KEY']
    return hashlib.sha256((key + value).encode('UTF-8')).hexdigest()
