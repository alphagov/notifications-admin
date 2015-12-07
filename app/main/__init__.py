from flask import Blueprint

main = Blueprint('main', __name__)


from app.main.views import index, sign_in, register, two_factor, verify
