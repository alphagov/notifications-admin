from werkzeug.routing import BaseConverter

from app.models.feedback import (
    GENERAL_TICKET_TYPE,
    PROBLEM_TICKET_TYPE,
    QUESTION_TICKET_TYPE,
)
from app.models.service import Service


class TemplateTypeConverter(BaseConverter):

    regex = "(?:{})".format("|".join(Service.TEMPLATE_TYPES))


class TicketTypeConverter(BaseConverter):

    regex = f"(?:{PROBLEM_TICKET_TYPE}|{QUESTION_TICKET_TYPE}|{GENERAL_TICKET_TYPE})"


class LetterFileExtensionConverter(BaseConverter):

    regex = "(?:pdf|png)"


class SimpleDateTypeConverter(BaseConverter):
    regex = r"([12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]))"
