from notifications_utils.formatters import formatted_list
from notifications_utils.serialised_model import SerialisedModelCollection
from werkzeug.utils import cached_property

from .polygons import Polygons
from .populations import CITY_OF_LONDON
from .repo import BroadcastAreasRepository


class SortableMixin:

    def __repr__(self):
        return f'{self.__class__.__name__}(<{self.id}>)'

    def __lt__(self, other):
        # Implementing __lt__ means any classes inheriting from this
        # method are sortable
        return self.name < other.name

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class GetItemByIdMixin:
    def get(self, id):
        for item in self:
            if item.id == id:
                return item
        raise KeyError(id)


class BroadcastArea(SortableMixin):

    def __init__(self, row):
        self.id, self.name, self._count_of_phones, self.library_id = row

    @cached_property
    def polygons(self):
        return Polygons(
            BroadcastAreasRepository().get_polygons_for_area(self.id)
        )

    @cached_property
    def simple_polygons(self):
        return Polygons(
            BroadcastAreasRepository().get_simple_polygons_for_area(self.id)
        )

    @cached_property
    def sub_areas(self):
        return [
            BroadcastArea(row)
            for row in BroadcastAreasRepository().get_all_areas_for_group(self.id)
        ]

    @property
    def count_of_phones(self):
        if self.id.endswith(CITY_OF_LONDON.WARDS):
            return CITY_OF_LONDON.DAYTIME_POPULATION * (
                self.polygons.estimated_area / CITY_OF_LONDON.AREA_SQUARE_MILES
            )
        if self.sub_areas:
            return sum(area.count_of_phones for area in self.sub_areas)
        # TODO: remove the `or 0` once missing data is fixed, see
        # https://www.pivotaltracker.com/story/show/174837293
        return self._count_of_phones or 0

    @cached_property
    def parents(self):
        return list(filter(None, self._parents_iterator))

    @property
    def _parents_iterator(self):
        id = self.id

        while True:
            parent = BroadcastAreasRepository().get_parent_for_area(id)

            if not parent:
                return None

            parent_broadcast_area = BroadcastArea(parent)

            yield parent_broadcast_area

            id = parent_broadcast_area.id


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
        # we show up to four things. three areas, then either a fourth area if there are exactly four, or "and X more".
        areas_to_show = sorted(area.name for area in self)[:4]

        count_of_areas_not_named = len(self.items) - 3
        # if there's exactly one area not named, there are exactly four - we should just show all four.
        if count_of_areas_not_named > 1:
            areas_to_show = areas_to_show[:3] + [f'{count_of_areas_not_named} more…']

        return formatted_list(areas_to_show, before_each='', after_each='')


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


broadcast_area_libraries = BroadcastAreaLibraries()
