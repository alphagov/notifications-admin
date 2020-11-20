from app.notify_client import NotifyAdminAPIClient, _attach_current_user, cache


class BroadcastMessageAPIClient(NotifyAdminAPIClient):

    def create_broadcast_message(
        self,
        *,
        service_id,
        template_id,
        content,
        reference,
    ):
        data = {
            "service_id": service_id,
            "personalisation": {},
        }
        if template_id:
            data.update(template_id=template_id)
        if content:
            data.update(content=content)
        if reference:
            data.update(reference=reference)

        data = _attach_current_user(data)

        broadcast_message = self.post(
            f'/service/{service_id}/broadcast-message',
            data=data,
        )

        return broadcast_message

    def get_broadcast_messages(self, service_id):
        return self.get(f'/service/{service_id}/broadcast-message')['broadcast_messages']

    @cache.set('service-{service_id}-broadcast-message-{broadcast_message_id}')
    def get_broadcast_message(self, *, service_id, broadcast_message_id):
        return self.get(f'/service/{service_id}/broadcast-message/{broadcast_message_id}')

    @cache.delete('service-{service_id}-broadcast-message-{broadcast_message_id}')
    def update_broadcast_message(self, *, service_id, broadcast_message_id, data):
        self.post(
            f'/service/{service_id}/broadcast-message/{broadcast_message_id}',
            data=data,
        )

    @cache.delete('service-{service_id}-broadcast-message-{broadcast_message_id}')
    def update_broadcast_message_status(self, status, *, service_id, broadcast_message_id):
        data = _attach_current_user({
            'status': status,
        })
        self.post(
            f'/service/{service_id}/broadcast-message/{broadcast_message_id}/status',
            data=data,
        )


broadcast_message_api_client = BroadcastMessageAPIClient()
