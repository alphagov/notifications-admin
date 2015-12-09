from random import randint
from app import admin_api_client
from app.main.exceptions import AdminApiClientException


def create_verify_code():
    return ''.join(["%s" % randint(0, 9) for _ in range(0, 5)])


def send_sms_code(mobile_number):
    sms_code = create_verify_code()
    try:
        admin_api_client.send_sms(mobile_number, message=sms_code, token=admin_api_client.auth_token)
    except:
        raise AdminApiClientException('Exception when sending sms.')
    return sms_code


def send_email_code(email):
    email_code = create_verify_code()
    try:
        admin_api_client.send_email(email_address=email,
                                    from_str='notify@digital.cabinet-office.gov.uk',
                                    message=email_code,
                                    subject='Verification code',
                                    token=admin_api_client.auth_token)
    except:
        raise AdminApiClientException('Exception when sending email.')

    return email_code
