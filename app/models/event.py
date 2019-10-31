from abc import ABC, abstractmethod

from notifications_utils.formatters import formatted_list

from app.models import ModelList
from app.notify_client.service_api_client import service_api_client
from app.utils import format_thousands


class Event(ABC):

    def __init__(
        self,
        item,
        key=None,
        value_from=None,
        value_to=None,
    ):
        self.item = item
        self.time = item['updated_at'] or item['created_at']
        self.user_id = item['created_by_id']
        self.key = key
        self.value_from = value_from
        self.value_to = value_to

    @abstractmethod
    def __str__(self):
        pass

    @property
    @abstractmethod
    def relevant(self):
        pass


class ServiceCreationEvent(Event):

    relevant = True

    def __str__(self):
        return 'Created this service and called it ‘{}’'.format(
            self.item['name']
        )


class ServiceEvent(Event):

    @property
    def relevant(self):
        return self.value_from != self.value_to and bool(self._formatter)

    def __str__(self):
        return self._formatter()

    @property
    def _formatter(self):
        return getattr(self, 'format_{}'.format(self.key), None)

    def format_restricted(self):
        if self.value_to is False:
            return 'Made this service live'
        if self.value_to is True:
            return 'Put this service back into trial mode'

    def format_active(self):
        if self.value_to is False:
            return 'Deleted this service'
        if self.value_to is True:
            return 'Unsuspended this service'

    def format_contact_link(self):
        return 'Set the contact details for this service to ‘{}’'.format(
            self.value_to
        )

    def format_email_branding(self):
        return 'Updated this service’s email branding'

    def format_inbound_api(self):
        return 'Updated the callback for received text messages'

    def format_letter_branding(self):
        if self.value_to is None:
            return 'Removed the logo from this service’s letters'
        return 'Updated the logo on this service’s letters'

    def format_letter_contact_block(self):
        return 'Updated the default letter contact block for this service'

    def format_message_limit(self):
        return (
            '{} this service’s daily message limit from {} to {}'
        ).format(
            'Reduced' if self.value_from > self.value_to else 'Increased',
            format_thousands(self.value_from),
            format_thousands(self.value_to),
        )

    def format_name(self):
        return (
            'Renamed this service from ‘{}’ to ‘{}’'
        ).format(
            self.value_from, self.value_to
        )

    def format_permissions(self):
        added = list(sorted(set(self.value_to) - set(self.value_from)))
        removed = list(sorted(set(self.value_from) - set(self.value_to)))
        if removed and added:
            return 'Removed {} from this service’s permissions, added {}'.format(
                formatted_list(removed),
                formatted_list(added),
            )
        if added:
            return 'Added {} to this service’s permissions'.format(
                formatted_list(added)
            )
        if removed:
            return 'Removed {} from this service’s permissions'.format(
                formatted_list(removed)
            )

    def format_prefix_sms(self):
        if self.value_to is True:
            return 'Set text messages to start with the name of this service'
        else:
            return 'Set text messages to not start with the name of this service'

    def format_research_mode(self):
        if self.value_to is True:
            return 'Put this service into research mode'
        else:
            return 'Took this service out of research mode'

    def format_service_callback_api(self):
        return 'Updated the callback for delivery receipts'

    def format_go_live_user(self):
        return 'Requested for this service to go live'


class APIKeyEvent(Event):

    relevant = True

    def __str__(self):
        if self.item['updated_at']:
            return (
                'Revoked the ‘{}’ API key'
            ).format(self.item['name'])
        else:
            return (
                'Created an API key called ‘{}’'
            ).format(self.item['name'])


class APIKeyEvents(ModelList):

    model = APIKeyEvent
    client = service_api_client.get_service_api_key_history


class ServiceEvents(ModelList):

    client = service_api_client.get_service_service_history

    @property
    def model(self):
        return lambda x: x

    @staticmethod
    def splat(events):
        for index, item in enumerate(sorted(
            events,
            key=lambda event: event['updated_at'] or event['created_at']
        )):
            if index == 0:
                yield ServiceCreationEvent(item)
            else:
                for key in sorted(item.keys()):
                    yield ServiceEvent(
                        item,
                        key,
                        events[index - 1][key],
                        events[index][key],
                    )

    def __init__(self, service_id):
        self.items = [
            event for event in self.splat(self.client(service_id)) if event.relevant
        ]
