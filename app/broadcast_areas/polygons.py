from shapely.geometry import (
    JOIN_STYLE,
    GeometryCollection,
    MultiPolygon,
    Polygon,
)
from shapely.ops import unary_union
from werkzeug.utils import cached_property


class Polygons():

    approx_metres_to_degree = 111_320

    # Estimated amount of bleed into neigbouring areas based on typical
    # range/separation of cell towers.
    approx_bleed_in_degrees = 1_500 / approx_metres_to_degree

    # Ratio of how much to buffer for a shape of a given perimeter. For
    # example `500` means 1m of buffer for every 500m of perimeter, or
    # 40m of buffer for a 5km square. This gives us control over how
    # much we fill in very concave features like channels, harbours and
    # zawns.
    perimeter_to_buffer_ratio = 500

    # Ratio of how much detail a shape of a given perimeter has once
    # simplified. Smaller number means more less detail. For example
    # `700` means that for a shape with a perimeter of 700m, the
    # simplified line will never deviate more than 1m from the original.
    # Or for a 5km square, the line won’t deviate more than 17m. This
    # gives us approximate control over the total number of points.
    perimeter_to_simplification_ratio = 700

    # The absolute smallest deviation (in metres) from the original we
    # allow no matter how big/small the shape is. Allows us to still
    # remove a bit of detail even for small shapes, for example urban
    # electoral wards.
    max_resolution = 5 / approx_metres_to_degree

    def __init__(self, polygons):
        if not polygons:
            self.polygons = []
        elif isinstance(polygons[0], list):
            self.polygons = [
                Polygon(polygon) for polygon in polygons
            ]
        else:
            self.polygons = polygons

    def __getitem__(self, index):
        return self.polygons[index]

    @cached_property
    def perimeter_length(self):
        return sum(
            polygon.length for polygon in self
        )

    @property
    def buffer_outward_in_degrees(self):
        return self.perimeter_length / self.perimeter_to_buffer_ratio

    @property
    def buffer_inward_in_degrees(self):
        return self.buffer_outward_in_degrees - (
            # We don’t want to buffer all the way back in because there
            # needs to be a bit off wiggle room for simplifying the
            # polygon. Theoretically we need
            # `self.simplification_tolerance_in_degrees` wiggle room,
            # but in practice some fraction of it is enough.
            self.simplification_tolerance_in_degrees * 2 / 3
        )

    @property
    def simplification_tolerance_in_degrees(self):
        shape_size_adjusted_resolution = (
            self.perimeter_length / self.perimeter_to_simplification_ratio
        )
        return self.max_resolution + shape_size_adjusted_resolution

    @cached_property
    def buffer_and_debuffer(self):
        buffered = [
            polygon.buffer(
                self.buffer_outward_in_degrees,
                resolution=4,
                join_style=JOIN_STYLE.round,
            )
            for polygon in self
        ]
        unioned = union_polygons(buffered)
        polygons_debuffered = [
            polygon.buffer(
                -1 * self.buffer_inward_in_degrees,
                resolution=1,
                join_style=JOIN_STYLE.bevel,
            )
            for polygon in unioned
        ]
        return Polygons(polygons_debuffered)

    @cached_property
    def simplify(self):
        return Polygons([
            polygon.simplify(self.simplification_tolerance_in_degrees)
            for polygon in self
        ])

    @cached_property
    def bleed(self):
        return Polygons(union_polygons([
            polygon.buffer(
                self.approx_bleed_in_degrees,
                resolution=4,
                join_style=JOIN_STYLE.round,
            )
            for polygon in self
        ]))

    @property
    def as_coordinate_pairs(self):
        return [
            [
                [x, y] for x, y in p.exterior.coords
            ]
            for p in self
        ]


def flatten_polygons(polygons):
    if isinstance(polygons, GeometryCollection):
        return []
    if isinstance(polygons, MultiPolygon):
        return [
            p for p in polygons
        ]
    else:
        return [polygons]


def union_polygons(polygons):
    return flatten_polygons(unary_union(polygons))
