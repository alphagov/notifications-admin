from random import randint
from flask import url_for, current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from app.main.dao import verify_codes_dao
from app import notifications_api_client


def create_verify_code():
    return ''.join(["%s" % randint(0, 9) for _ in range(0, 5)])


def send_sms_code(user_id, mobile_number):
    sms_code = create_verify_code()
    verify_codes_dao.add_code(user_id=user_id, code=sms_code, code_type='sms')
    notifications_api_client.send_sms(mobile_number=mobile_number,
                                      message=sms_code)
    return sms_code


def send_email_code(user_id, email):
    email_code = create_verify_code()
    verify_codes_dao.add_code(user_id=user_id, code=email_code, code_type='email')
    notifications_api_client.send_email(email_address=email,
                                        from_address='notify@digital.cabinet-office.gov.uk',
                                        message=email_code,
                                        subject='Verification code')
    return email_code


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
