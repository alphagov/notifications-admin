import itertools
from contextlib import suppress
from pathlib import Path
from functools import lru_cache
import sqlite3
import geojson
from notifications_utils.formatters import formatted_list

from notifications_utils.serialised_model import SerialisedModelCollection
from notifications_utils.safe_string import make_string_safe_for_id

from .repo import BroadcastAreasRepository


@lru_cache(maxsize=128)
def load_geojson_file(filename):

    path = Path(__file__).resolve().parent / filename

    geojson_data = geojson.loads(path.read_text())

    if not isinstance(geojson_data, geojson.GeoJSON) or not geojson_data.is_valid:
        raise ValueError(
            f'Contents of {path} are not valid GeoJSON'
        )

    return path.stem, geojson_data


class IdFromNameMixin:

    @property
    def id(self):
        return make_string_safe_for_id(self.name)

    def __repr__(self):
        return f'{self.__class__.__name__}(<{self.id}>)'

    def __lt__(self, other):
        # Implementing __lt__ means any classes inheriting from this
        # method are sortable
        return self.id < other.id


class GetItemByIdMixin:
    def get(self, id):
        for item in self:
            if item.id == id:
                return item
        raise KeyError(id)


class BroadcastArea(IdFromNameMixin):

    def __init__(self, feature):
        self.feature = feature

        for coordinates in self.polygons:
            if coordinates[0] != coordinates[-1]:
                # The CAP XML format requires shapes to be closed
                raise ValueError(
                    f'Area {self.name} is not a closed shape '
                    f'({coordinates[0]}, {coordinates[-1]})'
                )

    def __eq__(self, other):
        return self.id == other.id

    @property
    def name(self):
        for possible_name_key in {
            'rgn18nm', 'ctyua16nm', 'ctry19nm',
        }:
            with suppress(KeyError):
                return self.feature['properties'][possible_name_key]

        raise KeyError(f'No name found in {self.feature["properties"]}')

    @property
    def polygons(self):
        if self.feature['geometry']['type'] == 'MultiPolygon':
            return [
                polygons[0]
                for polygons in self.feature['geometry']['coordinates']
            ]
        if self.feature['geometry']['type'] == 'Polygon':
            return [
                self.feature['geometry']['coordinates'][0]
            ]
        raise TypeError(
            f'Unknown geometry type {self.feature["geometry"]["type"]} '
            f'in {self.__class__.__name} {self.name}'
        )

    @property
    def unenclosed_polygons(self):
        # Some mapping tools require shapes to be unenclosed, i.e. the
        # last point joins the first point implicitly
        return [
            coordinates[:-1] for coordinates in self.polygons
        ]


class BroadcastAreaLibrary(SerialisedModelCollection, IdFromNameMixin, GetItemByIdMixin):

    model = BroadcastArea

    def __init__(self, filename):
        self.name, geojson_data = load_geojson_file(filename)
        self.items = geojson_data['features']

    def get_examples(self, max_displayed=4):

        truncate_at = max_displayed - 1

        names = [area.name for area in sorted(self)]
        count_of_excess_names = len(names) - truncate_at

        if count_of_excess_names > 1:
            names = names[:truncate_at] + [f'{count_of_excess_names} more…']

        return formatted_list(names, before_each='', after_each='')


class BroadcastAreaLibraries(SerialisedModelCollection, GetItemByIdMixin):

    model = BroadcastAreaLibrary

    def __init__(self):

        self.items = list(
            Path(__file__).resolve().parent.glob('*.geojson')
        )

        self.all_areas = list(self.get_all_areas())

        seen_area_ids = set()

        for area_id in (area.id for area in self.all_areas):
            if area_id in seen_area_ids:
                raise ValueError(
                    f'{area_id} found more than once in '
                    f'{self.__class__.__name__}'
                )
            seen_area_ids.add(area_id)

    def get_all_areas(self):
        for library in self:
            for area in library:
                yield area

    def get_areas(self, *area_ids):
        # allow people to call `get_areas('a', 'b') or get_areas(['a', 'b'])`
        if len(area_ids) == 1 and isinstance(area_ids[0], list):
            area_ids = area_ids[0]

        return list(itertools.chain(*(
            [area for area in self.all_areas if area.id == area_id]
            for area_id in area_ids
        )))

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
