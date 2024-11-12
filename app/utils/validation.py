from notifications_utils.recipient_validation.errors import InvalidPhoneError
from notifications_utils.recipient_validation.phone_number import PhoneNumber


def format_phone_number_human_readable(number):
    try:
        phone_number = PhoneNumber(number)
    except InvalidPhoneError:
        # if there was a validation error, we want to shortcut out here, but still display the number on the front end
        return number
    return phone_number.get_human_readable_format()
