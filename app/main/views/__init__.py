from random import randint

from flask import url_for, current_app

from app import admin_api_client
from app.main.dao import verify_codes_dao


def create_verify_code():
    return ''.join(["%s" % randint(0, 9) for _ in range(0, 5)])


def send_sms_code(user_id, mobile_number):
    sms_code = create_verify_code()
    verify_codes_dao.add_code(user_id=user_id, code=sms_code, code_type='sms')
    admin_api_client.send_sms(mobile_number=mobile_number, message=sms_code, token=admin_api_client.auth_token)

    return sms_code


def send_email_code(user_id, email):
    email_code = create_verify_code()
    verify_codes_dao.add_code(user_id=user_id, code=email_code, code_type='email')
    admin_api_client.send_email(email_address=email,
                                from_str='notify@digital.cabinet-office.gov.uk',
                                message=email_code,
                                subject='Verification code',
                                token=admin_api_client.auth_token)
    return email_code


def send_change_password_email(email):
    link_to_change_password = url_for('.new_password', token=generate_token(email), _external=True)
    admin_api_client.send_email(email_address=email,
                                from_str='notify@digital.cabinet-office.gov.uk',
                                message=link_to_change_password,
                                subject='Reset password for GOV.UK Notify',
                                token=admin_api_client.auth_token)


def generate_token(email):
    from itsdangerous import TimestampSigner
    signer = TimestampSigner(current_app.config['SECRET_KEY'])
    return signer.sign(email).decode('utf8')


def check_token(token):
    from itsdangerous import TimestampSigner, SignatureExpired
    signer = TimestampSigner(current_app.config['SECRET_KEY'])
    try:
        email = signer.unsign(token, max_age=current_app.config['TOKEN_MAX_AGE_SECONDS'])
        return email
    except SignatureExpired as e:
        current_app.logger.info('token expired %s' % e)
