from werkzeug.routing import BaseConverter


class TemplateTypeConverter(BaseConverter):

    regex = '(?:email|sms|letter)'


class LetterFileExtensionConverter(BaseConverter):

    regex = '(?:pdf|png)'


class SimpleDateTypeConverter(BaseConverter):
    regex = r'([12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]))'
