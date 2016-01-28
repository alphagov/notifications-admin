from random import randint
from flask import url_for, current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from app import notifications_api_client


def send_change_password_email(email):
    link_to_change_password = url_for('.new_password', token=generate_token(email), _external=True)
    notifications_api_client.send_email(email_address=email,
                                        from_address='notify@digital.cabinet-office.gov.uk',
                                        message=link_to_change_password,
                                        subject='Reset password for GOV.UK Notify')


def generate_token(email):
    ser = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return ser.dumps(email, current_app.config.get('DANGEROUS_SALT'))


def check_token(token):
    ser = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = ser.loads(token, max_age=current_app.config['TOKEN_MAX_AGE_SECONDS'],
                          salt=current_app.config.get('DANGEROUS_SALT'))
        return email
    except SignatureExpired as e:
        current_app.logger.info('token expired %s' % e)
