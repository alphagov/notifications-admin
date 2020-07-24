import pytest
import re

from notifications_utils.broadcast_areas import (
    BroadcastAreasRepository,
    broadcast_area_libraries,
)


def test_loads_libraries():
    assert [
        (library.id, library.name) for library in sorted(broadcast_area_libraries)
    ] == [
        (
            'counties-and-unitary-authorities-in-england-and-wales',
            'Counties and Unitary Authorities in England and Wales'),
        (
            'countries',
            'Countries',
        ),
        (
            'electoral-wards-of-the-united-kingdom',
            'Electoral Wards of the United Kingdom',
        ),
        (
            'regions-of-england',
            'Regions of England',
        ),
    ]


def test_loads_areas_from_library():
    assert [
        (area.id, area.name) for area in sorted(
            broadcast_area_libraries.get('countries')
        )
    ] == [
        ('england', 'England'),
        ('northern-ireland', 'Northern Ireland'),
        ('scotland', 'Scotland'),
        ('wales', 'Wales'),
    ]


def test_examples():
    assert re.match(
        "^([^,]*, ){3}[^,]*",
        broadcast_area_libraries.get('countries').get_examples(),
    )
    assert re.match(
        "^([^,]*, ){4}5 more…$",
        broadcast_area_libraries.get('regions-of-england').get_examples()
    )


@pytest.mark.parametrize('id', (
    'england',
    'northern-ireland',
    'scotland',
    'wales',
    pytest.param('mercia', marks=pytest.mark.xfail(raises=KeyError)),
))
def test_loads_areas_from_libraries(id):
    assert (
        broadcast_area_libraries.get('countries').get(id)
    ) == (
        broadcast_area_libraries.get_areas(id)[0]
    )


def test_get_names_of_areas():
    areas = broadcast_area_libraries.get_areas(
        'wales', 'vale-of-glamorgan', 'england', 'essex',
    )
    assert [area.name for area in sorted(areas)] == [
        'England', 'Essex', 'Vale of Glamorgan', 'Wales',
    ]


def test_get_areas_accepts_lists():
    areas_from_list = broadcast_area_libraries.get_areas(
        ['wales', 'vale-of-glamorgan', 'england', 'essex']
    )
    areas_from_args = broadcast_area_libraries.get_areas(
        'wales', 'vale-of-glamorgan', 'england', 'essex',
    )
    assert areas_from_args == areas_from_list


def test_has_polygons():

    assert len(
        broadcast_area_libraries.get_polygons_for_areas_long_lat('england')
    ) == 35

    assert len(
        broadcast_area_libraries.get_polygons_for_areas_long_lat('scotland')
    ) == 195

    assert len(
        broadcast_area_libraries.get_polygons_for_areas_long_lat('england', 'scotland')
    ) == 35 + 195 == 230

    assert len(
        broadcast_area_libraries.get_polygons_for_areas_long_lat(['england', 'scotland'])
    ) == 35 + 195 == 230

    assert broadcast_area_libraries.get_polygons_for_areas_lat_long('england')[0][0] == [
        55.811085, -2.034358  # https://goo.gl/maps/wsf2LUWzYinwydMk8
    ]


def test_polygons_are_enclosed_unless_asked_not_to_be():

    england = broadcast_area_libraries.get('countries').get('england')

    assert len(england.polygons) == len(england.unenclosed_polygons)

    first_polygon = england.polygons[0]
    assert first_polygon[0] != first_polygon[1] != first_polygon[2]
    assert first_polygon[0] == first_polygon[-1]

    first_polygon_unenclosed = england.unenclosed_polygons[0]
    assert first_polygon_unenclosed[0] == first_polygon[0]
    assert first_polygon_unenclosed[-1] != first_polygon[-1]
    assert first_polygon_unenclosed[-1] == first_polygon[-2]


def test_lat_long_order():

    lat_long = broadcast_area_libraries.get_polygons_for_areas_lat_long('england')
    long_lat = broadcast_area_libraries.get_polygons_for_areas_long_lat('england')
    assert len(lat_long[0]) == len(long_lat[0]) == 2082  # Coordinates in polygon
    assert len(lat_long[0][0]) == len(long_lat[0][0]) == 2  # Axes in coordinates
    assert lat_long[0][0] == list(reversed(long_lat[0][0]))


def test_includes_electoral_wards():

    areas = broadcast_area_libraries.get_areas(['city-of-london---aldgate'])
    assert len(areas) == 1


def test_repository_has_all_libraries():
    repo = BroadcastAreasRepository()
    libraries = repo.get_libraries()

    assert len(libraries) == 4
    assert [
        'Counties and Unitary Authorities in England and Wales',
        'Countries',
        'Electoral Wards of the United Kingdom',
        'Regions of England',
    ] == sorted(libraries)
