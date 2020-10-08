import itertools
from datetime import datetime, timedelta

from notifications_utils.template import BroadcastPreviewTemplate
from orderedset import OrderedSet
from werkzeug.utils import cached_property

from app.broadcast_areas import broadcast_area_libraries
from app.broadcast_areas.polygons import Polygons
from app.models import JSONModel, ModelList
from app.models.user import User
from app.notify_client.broadcast_message_api_client import (
    broadcast_message_api_client,
)
from app.notify_client.service_api_client import service_api_client
from app.utils import round_to_significant_figures


class BroadcastMessage(JSONModel):

    ALLOWED_PROPERTIES = {
        'id',
        'service_id',
        'template_id',
        'template_name',
        'template_version',
        'content',
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
            self.cancelled_at or self.finishes_at or self.created_at
        ) < (
            other.cancelled_at or other.finishes_at or self.created_at
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
        return self.get_areas(areas=self._dict['areas'])

    @property
    def parent_areas(self):
        return sorted(set(self._parent_areas_iterator))

    @property
    def _parent_areas_iterator(self):
        for area in self.areas:
            for parent in area.parents:
                yield parent

    @property
    def initial_area_names(self):
        return [
            area.name for area in self.areas
        ][:10]

    @cached_property
    def polygons(self):
        return Polygons(
            list(itertools.chain(*(
                area.polygons for area in self.areas
            )))
        )

    @cached_property
    def simple_polygons(self):
        return self.get_simple_polygons(areas=self.areas)

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

    @property
    def count_of_phones(self):
        return round_to_significant_figures(
            sum(area.count_of_phones for area in self.areas),
            1
        )

    @property
    def count_of_phones_likely(self):
        area_estimate = self.simple_polygons.estimated_area
        bleed_area_estimate = self.simple_polygons.bleed.estimated_area - area_estimate
        return round_to_significant_figures(
            self.count_of_phones + (self.count_of_phones * bleed_area_estimate / area_estimate),
            1
        )

    def get_areas(self, areas):
        return broadcast_area_libraries.get_areas(
            *areas
        )

    def get_simple_polygons(self, areas):
        polygons = Polygons(
            list(itertools.chain(*(
                area.simple_polygons for area in areas
            )))
        )
        # If we’ve added multiple areas then we need to re-simplify the
        # combined shapes to keep the point count down
        return polygons.smooth.simplify if len(areas) > 1 else polygons

    def add_areas(self, *new_areas):
        areas = list(OrderedSet(
            self._dict['areas'] + list(new_areas)
        ))
        simple_polygons = self.get_simple_polygons(areas=self.get_areas(areas=areas))
        self._update(areas=areas, simple_polygons=simple_polygons.as_coordinate_pairs_lat_long)

    def remove_area(self, area_to_remove):
        areas = [
            area for area in self._dict['areas']
            if area != area_to_remove
        ]
        simple_polygons = self.get_simple_polygons(areas=self.get_areas(areas=areas))
        self._update(areas=areas, simple_polygons=simple_polygons.as_coordinate_pairs_lat_long)

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
