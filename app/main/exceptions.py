class AdminApiClientException(Exception):
    def __init__(self, message):
        self.value = message


class NoDataFoundException(Exception):
    def __init__(self, message):
        self.value = message
