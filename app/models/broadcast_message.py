from datetime import datetime, timedelta

from notifications_utils.template import BroadcastPreviewTemplate
from orderedset import OrderedSet
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union
from werkzeug.utils import cached_property

from app.broadcast_areas import broadcast_area_libraries
from app.models import JSONModel, ModelList
from app.models.user import User
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
        'created_at',
        'approved_at',
        'cancelled_at',
        'updated_at',
        'created_by_id',
        'approved_by_id',
        'cancelled_by_id',
    }

    libraries = broadcast_area_libraries

    def __lt__(self, other):
        return (
            self.cancelled_at or self.finishes_at
        ) < (
            other.cancelled_at or other.finishes_at
        )

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
    def initial_area_names(self):
        return [
            area.name for area in self.areas
        ][:10]

    @property
    def polygons(self):
        return broadcast_area_libraries.get_polygons_for_areas_lat_long(
            *self._dict['areas']
        )

    @property
    def simple_polygons(self):
        simple_polygons = broadcast_area_libraries.get_simple_polygons_for_areas_lat_long(
            *self._dict['areas']
        )
        unioned_polygons = unary_union([
            Polygon(i) for i in simple_polygons
        ])
        if isinstance(unioned_polygons, MultiPolygon):
            return [
                [
                    [x, y] for x, y in p.exterior.coords
                ]
                for p in unioned_polygons
            ]
        return [[
            [x, y] for x, y in unioned_polygons.exterior.coords
        ]]

    @property
    def template(self):
        response = service_api_client.get_service_template(
            self.service_id,
            self.template_id,
            version=self.template_version,
        )
        return BroadcastPreviewTemplate(response['data'])

    @property
    def status(self):
        if (
            self._dict['status']
            and self._dict['status'] == 'broadcasting'
            and self.finishes_at < datetime.utcnow().isoformat()
        ):
            return 'completed'
        return self._dict['status']

    @cached_property
    def created_by(self):
        return User.from_id(self.created_by_id)

    @cached_property
    def approved_by(self):
        return User.from_id(self.approved_by_id)

    @cached_property
    def cancelled_by(self):
        return User.from_id(self.cancelled_by_id)

    def add_areas(self, *new_areas):
        self._update(areas=list(OrderedSet(
            self._dict['areas'] + list(new_areas)
        )))

    def remove_area(self, area_to_remove):
        self._update(areas=[
            area for area in self._dict['areas']
            if area != area_to_remove
        ])

    def _set_status_to(self, status):
        broadcast_message_api_client.update_broadcast_message_status(
            status,
            broadcast_message_id=self.id,
            service_id=self.service_id,
        )

    def _update(self, **kwargs):
        broadcast_message_api_client.update_broadcast_message(
            broadcast_message_id=self.id,
            service_id=self.service_id,
            data=kwargs,
        )

    def request_approval(self):
        self._set_status_to('pending-approval')

    def approve_broadcast(self):
        self._update(
            starts_at=datetime.utcnow().isoformat(),
            finishes_at=(
                datetime.utcnow() + timedelta(hours=23, minutes=59)
            ).isoformat(),
        )
        self._set_status_to('broadcasting')

    def reject_broadcast(self):
        self._set_status_to('rejected')

    def cancel_broadcast(self):
        self._set_status_to('cancelled')


class BroadcastMessages(ModelList):

    model = BroadcastMessage
    client_method = broadcast_message_api_client.get_broadcast_messages

    def with_status(self, *statuses):
        return [
            broadcast for broadcast in self if broadcast.status in statuses
        ]
