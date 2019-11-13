from werkzeug.routing import BaseConverter


class TemplateTypeConverter(BaseConverter):

    regex = '(?:email|sms|letter)'


class LetterFileExtensionConverter(BaseConverter):

    regex = '(?:pdf|png)'
