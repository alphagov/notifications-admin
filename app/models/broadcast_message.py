from datetime import datetime, timedelta

from notifications_utils.broadcast_areas import broadcast_area_libraries
from notifications_utils.template import BroadcastPreviewTemplate
from orderedset import OrderedSet

from app.models import JSONModel
from app.notify_client.broadcast_message_api_client import (
    broadcast_message_api_client,
)
from app.notify_client.service_api_client import service_api_client


class BroadcastMessage(JSONModel):

    ALLOWED_PROPERTIES = {
        'id',
        'service_id',
        'template_id',
        'template_name',
        'template_version',
        'service_id',
        'created_by',
        'personalisation',
        'starts_at',
        'finishes_at',
        'status',
        'created_at',
        'approved_at',
        'cancelled_at',
        'updated_at',
        'created_by_id',
        'approved_by_id',
        'cancelled_by_id',
    }
    DEFAULT_TTL = timedelta(hours=72)

    libraries = broadcast_area_libraries

    @classmethod
    def create(cls, *, service_id, template_id):
        return cls(broadcast_message_api_client.create_broadcast_message(
            service_id=service_id,
            template_id=template_id,
        ))

    @classmethod
    def from_id(cls, broadcast_message_id, *, service_id):
        return cls(broadcast_message_api_client.get_broadcast_message(
            service_id=service_id,
            broadcast_message_id=broadcast_message_id,
        ))

    @property
    def areas(self):
        return broadcast_area_libraries.get_areas(
            *self._dict['areas']
        )

    @property
    def polygons(self):
        return broadcast_area_libraries.get_polygons_for_areas_lat_long(
            *self._dict['areas']
        )

    @property
    def template(self):
        response = service_api_client.get_service_template(
            self.service_id,
            self.template_id,
            version=self.template_version,
        )
        return BroadcastPreviewTemplate(response['data'])

    def add_areas(self, *new_areas):
        broadcast_message_api_client.update_broadcast_message(
            broadcast_message_id=self.id,
            service_id=self.service_id,
            data={
                'areas': list(OrderedSet(
                    self._dict['areas'] + list(new_areas)
                ))
            },
        )

    def remove_area(self, area_to_remove):
        broadcast_message_api_client.update_broadcast_message(
            broadcast_message_id=self.id,
            service_id=self.service_id,
            data={
                'areas': [
                    area for area in self._dict['areas']
                    if area != area_to_remove
                ]
            },
        )

    def start_broadcast(self):
        broadcast_message_api_client.update_broadcast_message(
            broadcast_message_id=self.id,
            service_id=self.service_id,
            data={
                'starts_at': datetime.utcnow().isoformat(),
                'finishes_at': (datetime.utcnow() + self.DEFAULT_TTL).isoformat(),
            },
        )
        broadcast_message_api_client.update_broadcast_message_status(
            'broadcasting',
            broadcast_message_id=self.id,
            service_id=self.service_id,
        )
