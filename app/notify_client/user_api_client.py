from client.notifications import BaseAPIClient


class UserApiClient(BaseAPIClient):

    def __init__(self, base_url, client_id, secret):
        super(self.__class__, self).__init__(base_url=base_url,
                                             client_id=client_id,
                                             secret=secret)

    def register_user(self, name, email_address,  mobile_number, password):
        data = {
            "name": name,
            "email_address": email_address,
            "mobile_number": mobile_number,
            "password": password}

        return self.post("/user", data)
