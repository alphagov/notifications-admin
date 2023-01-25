EMAIL_LOGO_LOCATION_STRUCTURE = "{temp}{unique_id}-{filename}"
LETTER_PREFIX = "letters/static/images/letter-template/"


def permanent_letter_logo_name(filename, extension):
    return LETTER_PREFIX + filename + "." + extension
