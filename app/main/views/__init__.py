from random import randint
from app import admin_api_client
from app.main.exceptions import AdminApiClientException
from app.main.dao import verify_codes_dao


def create_verify_code():
    return ''.join(["%s" % randint(0, 9) for _ in range(0, 5)])


def send_sms_code(user_id, mobile_number):
    sms_code = create_verify_code()
    try:
        verify_codes_dao.add_code(user_id=user_id, code=sms_code, code_type='sms')
        admin_api_client.send_sms(mobile_number, message=sms_code, token=admin_api_client.auth_token)
    except:
        raise AdminApiClientException('Exception when sending sms.')
    return sms_code


def send_email_code(user_id, email):
    email_code = create_verify_code()
    try:
        verify_codes_dao.add_code(user_id=user_id, code=email_code, code_type='email')
        admin_api_client.send_email(email_address=email,
                                    from_str='notify@digital.cabinet-office.gov.uk',
                                    message=email_code,
                                    subject='Verification code',
                                    token=admin_api_client.auth_token)
    except:
        raise AdminApiClientException('Exception when sending email.')

    return email_code
