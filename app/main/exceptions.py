

class AdminApiClientException(Exception):
    def __init__(self, message):
        self.value = message
