from abc import ABC, abstractmethod

from notifications_utils.formatters import formatted_list

from app.formatters import format_thousands
from app.models import ModelList
from app.notify_client.service_api_client import service_api_client


class Event(ABC):
    def __init__(
        self,
        item,
        key=None,
        value_from=None,
        value_to=None,
    ):
        self.item = item
        self.time = item["updated_at"] or item["created_at"]
        self.user_id = item["created_by_id"]
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
        return f"Heeft deze service gemaakt en noemde het ‘{self.item['name']}’"


class ServiceEvent(Event):
    @property
    def relevant(self):
        return self.value_from != self.value_to and bool(self._formatter)

    def __str__(self):
        return self._formatter()

    @property
    def _formatter(self):
        return getattr(self, f"format_{self.key}", None)

    def format_restricted(self):
        if self.value_to is False:
            return "Maakte deze service live"
        if self.value_to is True:
            return "Zet deze service weer in proefmodus"

    def format_active(self):
        if self.value_to is False:
            return "Deleted this service"
        if self.value_to is True:
            return "Deze service niet -ondersteund"

    def format_contact_link(self):
        return f"Stel de contactgegevens in voor deze service op ‘{self.value_to}’"

    def format_message_limit(self):
        return "{} de dagelijkse berichtlimiet van deze service van {} naar {}".format(
            "Reduced" if self.value_from > self.value_to else "Increased",
            format_thousands(self.value_from),
            format_thousands(self.value_to),
        )

    def format_sms_message_limit(self):
        return "{} de dagelijkse sms -limiet van deze service van {} naar {}".format(
            "Reduced" if self.value_from > self.value_to else "Increased",
            format_thousands(self.value_from),
            format_thousands(self.value_to),
        )

    def format_email_message_limit(self):
        return "{} de dagelijkse e -maillimiet van deze service van {} naar {}".format(
            "Reduced" if self.value_from > self.value_to else "Increased",
            format_thousands(self.value_from),
            format_thousands(self.value_to),
        )

    def format_letter_message_limit(self):
        return "{} de dagelijkse letterlimiet van deze service van {} naar {}".format(
            "Reduced" if self.value_from > self.value_to else "Increased",
            format_thousands(self.value_from),
            format_thousands(self.value_to),
        )

    def format_name(self):
        return f"Hernoemde deze service van ‘{self.value_from}’ naar ‘{self.value_to}’"

    def format_permissions(self):
        added = sorted(set(self.value_to) - set(self.value_from))
        removed = sorted(set(self.value_from) - set(self.value_to))
        if removed and added:
            return (
                f"Verwijderde {formatted_list(removed)} uit de machtigingen van deze service, "
                f"toegevoegd {formatted_list(added)}"
            )
        if added:
            return f"{formatted_list(added)} toegevoegd aan de machtigingen van deze service"
        if removed:
            return f"{formatted_list(removed)} verwijderd uit de machtigingen van deze service"

    def format_prefix_sms(self):
        if self.value_to is True:
            return "Stel tekstberichten in om te beginnen met de naam van deze service"
        else:
            return "Stel tekstberichten in om niet te beginnen met de naam van deze service"

    def format_service_callback_api(self):
        return "De callback bijgewerkt voor leveringsontvangsten"

    def format_go_live_user(self):
        return "Gevraagd voor deze service om live te gaan"


class APIKeyEvent(Event):
    relevant = True

    def __str__(self):
        if self.item["updated_at"]:
            return f"De ‘{self.item['name']}’ API -sleutel ingetrokken"
        else:
            return f"Een API -sleutel gemaakt met de naam ‘{self.item['name']}’"


class APIKeyEvents(ModelList):
    model = APIKeyEvent

    @staticmethod
    def _get_items(*args, **kwargs):
        return service_api_client.get_service_api_key_history(*args, **kwargs)


class ServiceEvents(ModelList):
    @property
    def model(self):
        return lambda x: x

    @staticmethod
    def _get_items(*args, **kwargs):
        return service_api_client.get_service_service_history(*args, **kwargs)

    @staticmethod
    def splat(events):
        sorted_events = sorted(events, key=lambda event: event["updated_at"] or event["created_at"])
        for index, item in enumerate(sorted_events):
            if index == 0:
                yield ServiceCreationEvent(item)
            else:
                for key in sorted(item.keys()):
                    yield ServiceEvent(
                        item,
                        key,
                        sorted_events[index - 1][key],
                        sorted_events[index][key],
                    )

    def __init__(self, service_id):
        self.items = [event for event in self.splat(self._get_items(service_id)) if event.relevant]
