import itertools
from datetime import datetime, timedelta

from flask import current_app
from notifications_utils.polygons import Polygons
from notifications_utils.template import BroadcastPreviewTemplate
from orderedset import OrderedSet
from werkzeug.utils import cached_property

from app.broadcast_areas.models import (
    CustomBroadcastArea,
    CustomBroadcastAreas,
    broadcast_area_libraries,
)
from app.broadcast_areas.utils import aggregate_areas
from app.formatters import round_to_significant_figures
from app.models import JSONModel, ModelList
from app.models.user import User
from app.notify_client.broadcast_message_api_client import (
    broadcast_message_api_client,
)

ESTIMATED_AREA_OF_LARGEST_UK_COUNTY = broadcast_area_libraries.get_areas([
    'ctyua19-E10000023'  # North Yorkshire
])[0].polygons.estimated_area


class BroadcastMessage(JSONModel):

    ALLOWED_PROPERTIES = {
        'id',
        'service_id',
        'template_id',
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
        if self.starts_at and other.starts_at:
            return self.starts_at < other.starts_at
        if self.starts_at and not other.starts_at:
            return True
        if not self.starts_at and other.starts_at:
            return False
        if self.updated_at and not other.updated_at:
            return self.updated_at < other.created_at
        if not self.updated_at and other.updated_at:
            return self.created_at < other.updated_at
        if not self.updated_at and not other.updated_at:
            return self.created_at < other.created_at
        return self.updated_at < other.updated_at

    @classmethod
    def create(cls, *, service_id, template_id):
        return cls(broadcast_message_api_client.create_broadcast_message(
            service_id=service_id,
            template_id=template_id,
            content=None,
            reference=None,
        ))

    @classmethod
    def create_from_content(cls, *, service_id, content, reference):
        return cls(broadcast_message_api_client.create_broadcast_message(
            service_id=service_id,
            template_id=None,
            content=content,
            reference=reference,
        ))

    @classmethod
    def from_id(cls, broadcast_message_id, *, service_id):
        return cls(broadcast_message_api_client.get_broadcast_message(
            service_id=service_id,
            broadcast_message_id=broadcast_message_id,
        ))

    @property
    def areas(self):
        if 'ids' in self._dict['areas']:
            library_areas = self.get_areas(self.area_ids)

            if len(library_areas) == len(self.area_ids):
                return library_areas
            else:
                # it's possible an old broadcast may refer to areas that
                # are no longer part of our area libraries; in this case
                # we should just treat the whole thing as a custom broadcast,
                # which isn't great as our code doesn't support editing its
                # areas, but we don't expect this to happen often
                current_app.logger.warn(
                    f'BroadcastMessage has {len(self.area_ids)} area IDs '
                    f'but {len(library_areas)} found in the library. Treating '
                    f'{self.id} as a custom broadcast.'
                )

        polygons = self._dict['areas'].get('simple_polygons', [])

        if polygons:
            return CustomBroadcastAreas(
                names=self._dict['areas']['names'],
                polygons=polygons,
            )

        return []

    @property
    def area_ids(self):
        return self._dict['areas'].get('ids', [])

    @area_ids.setter
    def area_ids(self, value):
        self._dict['areas']['ids'] = value

    @property
    def ancestor_areas(self):
        return sorted(set(self._ancestor_areas_iterator))

    @property
    def _ancestor_areas_iterator(self):
        for area in self.areas:
            for ancestor in area.ancestors:
                yield ancestor

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

    @cached_property
    def simple_polygons_with_bleed(self):
        polygons = Polygons(
            list(itertools.chain(*(
                area.simple_polygons_with_bleed for area in self.areas
            )))
        )
        # If we’ve added multiple areas then we need to re-simplify the
        # combined shapes to keep the point count down
        return polygons.smooth.simplify if len(self.areas) > 1 else polygons

    @property
    def reference(self):
        if self.template_id:
            return self._dict['template_name']
        return self._dict['cap_event'] or self._dict['reference']

    @property
    def template(self):
        return BroadcastPreviewTemplate({
            'template_type': BroadcastPreviewTemplate.template_type,
            'name': self.reference,
            'content': self.content,
        })

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
        return User.from_id(self.created_by_id) if self.created_by_id else None

    @cached_property
    def approved_by(self):
        return User.from_id(self.approved_by_id) if self.approved_by_id else None

    @cached_property
    def cancelled_by(self):
        return User.from_id(self.cancelled_by_id)

    @cached_property
    def count_of_phones(self):
        return round_to_significant_figures(
            sum(area.count_of_phones for area in self.areas),
            1
        )

    @cached_property
    def count_of_phones_likely(self):
        estimated_area = self.simple_polygons.estimated_area

        if estimated_area > ESTIMATED_AREA_OF_LARGEST_UK_COUNTY:
            # For large areas, use a naïve but computationally less
            # expensive way of counting the number of phones in the
            # bleed area
            count = self.count_of_phones * (
                self.simple_polygons_with_bleed.estimated_area / estimated_area
            )
        else:
            # For smaller areas, where the computation can be done in
            # a second or less (approximately) calculate the number of
            # phones based on the ammount of overlap with areas for
            # which we have population data
            count = CustomBroadcastArea.from_polygon_objects(
                self.simple_polygons_with_bleed
            ).count_of_phones

        return round_to_significant_figures(count, 1)

    def get_areas(self, area_ids):
        return broadcast_area_libraries.get_areas(
            area_ids
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

    def add_areas(self, *new_area_ids):
        self.area_ids = list(OrderedSet(self.area_ids + list(new_area_ids)))
        self._update_areas()

    def remove_area(self, area_id):
        self.area_ids = list(set(self._dict['areas']['ids']) - {area_id})
        self._update_areas()

    def _set_status_to(self, status):
        broadcast_message_api_client.update_broadcast_message_status(
            status,
            broadcast_message_id=self.id,
            service_id=self.service_id,
        )

    def _update_areas(self, force_override=False):
        areas = {
            'ids': self.area_ids,
            'names': [area.name for area in self.areas],
            'aggregate_names': [area.name for area in aggregate_areas(self.areas)],
            'simple_polygons': self.simple_polygons.as_coordinate_pairs_lat_long
        }

        data = {'areas': areas}

        # TEMPORARY: while we migrate to a new format for "areas"
        if force_override:
            data['force_override'] = True

        self._update(**data)

    def _update(self, **kwargs):
        broadcast_message_api_client.update_broadcast_message(
            broadcast_message_id=self.id,
            service_id=self.service_id,
            data=kwargs,
        )

    def request_approval(self):
        self._set_status_to('pending-approval')

    def approve_broadcast(self, channel):
        if channel in {'test', 'operator'}:
            ttl = timedelta(hours=4, minutes=0)
        else:
            ttl = timedelta(hours=22, minutes=30)

        self._update(
            starts_at=datetime.utcnow().isoformat(),
            finishes_at=(datetime.utcnow() + ttl).isoformat(),
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
