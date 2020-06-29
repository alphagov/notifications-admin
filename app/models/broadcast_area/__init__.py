import itertools
from pathlib import Path
from functools import lru_cache
import geojson
from notifications_utils.formatters import formatted_list

from app.models import ModelList
from app.utils import id_safe


@lru_cache(maxsize=128)
def load_geojson_file(filename):

    path = Path(__file__).resolve().parent / filename

    geojson_data = geojson.loads(path.read_text())

    if not geojson_data.is_valid:
        raise ValueError(
            f'Contents of {path} are not valid GeoJSON'
        )

    return path.stem, geojson_data


class IdFromNameMixin:

    @property
    def id(self):
        return id_safe(self.name)

    def __repr__(self):
        return f'{self.__class__.__name__}(<{self.id}>)'


class GetByIdMixin:
    def get(self, id):
        for item in self:
            if item.id == id:
                return item
        raise KeyError(id)


class BroadcastRegion(IdFromNameMixin):

    def __init__(self, feature, *, parent):

        self.feature = feature
        self.parent = parent

        for area in self.areas:
            if area[0] != area[-1]:
                raise ValueError(
                    f'Area {self.name} is not a closed shape '
                    f'({area[0]}, {area[-1]})'
                )

    @property
    def name(self):
        for possible_name_key in (
            'rgn18nm', 'ctyua16nm', 'ctry19nm',
        ):
            try:
                return self.feature['properties'][possible_name_key]
            except KeyError:
                pass
        raise KeyError(f'No name found in {self.feature["properties"]}')

    @property
    def areas(self):
        if self.feature['geometry']['type'] == 'MultiPolygon':
            return [
                area[0]
                for area in self.feature['geometry']['coordinates']
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
    def unenclosed_areas(self):
        return [
            area[1:] for area in self.areas
        ]


class BroadcastRegionLibrary(ModelList, IdFromNameMixin, GetByIdMixin):

    model = BroadcastRegion

    def __getitem__(self, index):
        return self.model(self.items[index], parent=self)

    def client_method(self, filename):

        self.name, geojson_data = load_geojson_file(filename)

        return geojson_data['features']

    @property
    def examples(self):

        max_displayed = 4
        truncate_at = max_displayed - 1

        names = [area.name for area in self]
        excess_names = len(names) - truncate_at

        if excess_names > 1:
            names = names[:truncate_at] + [f'{excess_names} more…']

        return formatted_list(names, before_each='', after_each='')


class BroadcastRegionLibraries(ModelList, GetByIdMixin):

    model = BroadcastRegionLibrary

    @staticmethod
    def client_method():
        return list(
            Path(__file__).resolve().parent.glob('*.geojson')
        )

    def __init__(self):

        super().__init__()

        self.all_regions = list(self.get_all_regions())
        self.all_region_ids = list(region.id for region in self.all_regions)

        for region_id in self.all_region_ids:
            if self.all_region_ids.count(region_id) != 1:
                raise ValueError(
                    f'{region_id} found more than once in {self.__class__.__name__}'
                )

    def get_all_regions(self):
        for library in self:
            for region in library:
                yield region

    def get_regions(self, *region_ids):
        for region_id in region_ids:
            for region in self.all_regions:
                if region.id == region_id:
                    yield region

    def get_geojson_features_for_regions(self, *regions):
        return [
            geojson.dumps(region.feature)
            for region in self.get_regions(*regions)
        ]

    def get_area_polygons_for_regions_long_lat(self, *regions):
        return list(itertools.chain(*(
            region.areas
            for region in self.get_regions(*regions)
        )))

    def get_area_polygons_for_regions_lat_long(self, *regions):
        for area in self.get_area_polygons_for_regions_long_lat(*regions):
            yield [
                [long, lat] for lat, long in area
            ]


broadcast_region_libraries = BroadcastRegionLibraries()
