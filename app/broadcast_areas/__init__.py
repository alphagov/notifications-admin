import itertools

import geojson
from notifications_utils.serialised_model import SerialisedModelCollection
from operator import itemgetter
from werkzeug.utils import cached_property

from .repo import BroadcastAreasRepository


class SortableMixin:

    def __repr__(self):
        return f'{self.__class__.__name__}(<{self.id}>)'

    def __lt__(self, other):
        # Implementing __lt__ means any classes inheriting from this
        # method are sortable
        return self.name < other.name


class GetItemByIdMixin:
    def get(self, id):
        for item in self:
            if item.id == id:
                return item
        raise KeyError(id)


class BroadcastArea(SortableMixin):

    def __init__(self, row):
        self.id, self.name = row

    def __eq__(self, other):
        return self.id == other.id

    @property
    def _feature(self):
        return BroadcastAreasRepository().get_feature_for_area(self.id)

    @property
    def _simple_feature(self):
        return BroadcastAreasRepository().get_simple_feature_for_area(self.id)

    def _polygons(self, feature):
        if feature['geometry']['type'] == 'MultiPolygon':
            return [
                polygons[0]
                for polygons in feature['geometry']['coordinates']
            ]
        if feature['geometry']['type'] == 'Polygon':
            return [
                feature['geometry']['coordinates'][0]
            ]
        raise TypeError(
            f'Unknown geometry type {self.feature["geometry"]["type"]} '
            f'in {self.__class__.__name} {self.name}'
        )

    def _unenclosed_polygons(self, feature):
        # Some mapping tools require shapes to be unenclosed, i.e. the
        # last point joins the first point implicitly
        return [
            coordinates[:-1] for coordinates in self._polygons(feature)
        ]

    @property
    def polygons(self):
        return self._polygons(self.feature)

    @property
    def unenclosed_polygons(self):
        return self._unenclosed_polygons(self.feature)

    @property
    def simple_polygons(self):
        return self._polygons(self.simple_feature)

    @property
    def simple_unenclosed_polygons(self):
        return self._unenclosed_polygons(self.simple_feature)

    @cached_property
    def feature(self):
        return geojson.loads(self._feature)

    @cached_property
    def simple_feature(self):
        return geojson.loads(self._simple_feature)

    @property
    def sub_areas(self):
        return [
            BroadcastArea(row)
            for row in BroadcastAreasRepository().get_all_areas_for_group(self.id)
        ]


class BroadcastAreaLibrary(SerialisedModelCollection, SortableMixin, GetItemByIdMixin):

    model = BroadcastArea

    def __init__(self, row):
        id, name, name_singular, is_group = row
        self.id = id
        self.name = name
        self.name_singular = name_singular
        self.is_group = bool(is_group)
        self.items = BroadcastAreasRepository().get_all_areas_for_library(self.id)

    def get_examples(self):
        return BroadcastAreasRepository().get_library_description(self.id)


class BroadcastAreaLibraries(SerialisedModelCollection, GetItemByIdMixin):

    model = BroadcastAreaLibrary

    def __init__(self):
        self.items = BroadcastAreasRepository().get_libraries()

    def get_areas(self, *area_ids):
        # allow people to call `get_areas('a', 'b') or get_areas(['a', 'b'])`
        if len(area_ids) == 1 and isinstance(area_ids[0], list):
            area_ids = area_ids[0]

        areas = BroadcastAreasRepository().get_areas(area_ids)
        return [BroadcastArea(area) for area in areas]

    def get_polygons_for_areas_long_lat(self, *area_ids):
        return list(itertools.chain(*(
            area.polygons
            for area in self.get_areas(*area_ids)
        )))

    def get_polygons_for_areas_lat_long(self, *area_ids):
        return [
            [[long, lat] for lat, long in polygon]
            for polygon in self.get_polygons_for_areas_long_lat(*area_ids)
        ]

    def get_simple_polygons_for_areas_long_lat(self, *area_ids):
        return list(itertools.chain(*(
            area.simple_polygons
            for area in self.get_areas(*area_ids)
        )))

    def get_simple_polygons_for_areas_lat_long(self, *area_ids):
        return [
            [[long, lat] for lat, long in polygon]
            for polygon in self.get_simple_polygons_for_areas_long_lat(*area_ids)
        ]

    def get_common_ancestor_for_areas(self, *area_ids):
        libraries, groups = (
            set(map(itemgetter(attr), self.get_areas(*area_ids)))
            for attr in (
                'library_id', 'group_id',
            )
        )

        def _get_singular_item_from_iterable(iterable):
            return next(iter(libraries)) if len(libraries) == 1 else None

        return (
            _get_singular_item_from_iterable(libraries),
            _get_singular_item_from_iterable(groups),
        )


broadcast_area_libraries = BroadcastAreaLibraries()
