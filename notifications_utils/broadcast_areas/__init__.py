import geojson
import itertools

from notifications_utils.serialised_model import SerialisedModelCollection
from notifications_utils.safe_string import make_string_safe_for_id

from .repo import BroadcastAreasRepository


class IdentifiableMixin:

    def __repr__(self):
        return f'{self.__class__.__name__}(<{self.id}>)'

    def __lt__(self, other):
        # Implementing __lt__ means any classes inheriting from this
        # method are sortable
        return self.id < other.id


class IdFromNameMixin:

    @property
    def id(self):
        return make_string_safe_for_id(self.name)


class GetItemByIdMixin:
    def get(self, id):
        for item in self:
            if item.id == id:
                return item
        raise KeyError(id)


class BroadcastArea(IdentifiableMixin):

    def __init__(self, row):
        id, name, feature, simple_feature = row

        self.id = id
        self.name = name
        self._feature = feature
        self._simple_feature = simple_feature

        for coordinates in self.polygons:
            if coordinates[0] != coordinates[-1]:
                # The CAP XML format requires shapes to be closed
                raise ValueError(
                    f'Area {self.name} is not a closed shape '
                    f'({coordinates[0]}, {coordinates[-1]})'
                )

    def __eq__(self, other):
        return self.id == other.id

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

    @property
    def feature(self):
        return geojson.loads(self._feature)

    @property
    def simple_feature(self):
        return geojson.loads(self._simple_feature)


class BroadcastAreaLibrary(SerialisedModelCollection, IdentifiableMixin, IdFromNameMixin, GetItemByIdMixin):

    model = BroadcastArea

    def __init__(self, library_name):
        self.name = library_name

    def get_examples(self):
        return BroadcastAreasRepository().get_library_description(self.id)

    @property
    def items(self):
        return BroadcastAreasRepository().get_all_areas_for_library(self.id)


class BroadcastAreaLibraries(SerialisedModelCollection, GetItemByIdMixin):

    model = BroadcastAreaLibrary

    def __init__(self):

        self.libraries = BroadcastAreasRepository().get_libraries()
        self.items = self.libraries

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


broadcast_area_libraries = BroadcastAreaLibraries()
