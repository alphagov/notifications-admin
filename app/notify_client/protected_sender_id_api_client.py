from app.notify_client import NotifyAdminAPIClient


class ProtectedSenderIDApiClient(NotifyAdminAPIClient):

    def get_check_sender_id(self, sender_id):
        return self.get(url="/protected-sender-id/check", params={"sender_id": sender_id})


protected_sender_id_api_client = ProtectedSenderIDApiClient()
