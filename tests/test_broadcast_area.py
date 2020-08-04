import pytest
import re

from notifications_utils.broadcast_areas import (
    BroadcastAreasRepository,
    broadcast_area_libraries,
)


def test_loads_libraries():
    assert [
        (library.id, library.name, library.is_group) for library in sorted(broadcast_area_libraries)
    ] == [
        (
            'counties-and-unitary-authorities-in-england-and-wales',
            'Counties and Unitary Authorities in England and Wales',
            False,
        ),
        (
            'countries',
            'Countries',
            False,
        ),
        (
            'electoral-wards-of-the-united-kingdom',
            'Electoral Wards of the United Kingdom',
            True,
        ),
        (
            'regions-of-england',
            'Regions of England',
            False,
        ),
    ]


def test_loads_areas_from_library():
    assert [
        (area.id, area.name) for area in sorted(
            broadcast_area_libraries.get('countries')
        )
    ] == [
        ('countries-E92000001', 'England'),
        ('countries-N92000002', 'Northern Ireland'),
        ('countries-S92000003', 'Scotland'),
        ('countries-W92000004', 'Wales'),
    ]


def test_examples():
    assert re.match(
        "^([^,]*, ){3}[^,]*",
        broadcast_area_libraries.get('countries').get_examples(),
    )
    assert re.match(
        "^([^,]*, ){4}and 5 more…$",
        broadcast_area_libraries.get('regions-of-england').get_examples()
    )


@pytest.mark.parametrize('id', (
    'countries-E92000001',
    'countries-N92000002',
    'countries-S92000003',
    'countries-W92000004',
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
        'countries-W92000004',
        'electoral-wards-of-the-united-kingdom-W06000014',
        'countries-E92000001',
        'counties-and-unitary-authorities-in-england-and-wales-E10000012',

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
        broadcast_area_libraries.get_polygons_for_areas_long_lat('countries-E92000001')
    ) == 35

    assert len(
        broadcast_area_libraries.get_polygons_for_areas_long_lat('countries-S92000003')
    ) == 195

    assert len(
        broadcast_area_libraries.get_polygons_for_areas_long_lat(
            'countries-E92000001',
            'countries-S92000003',
        )
    ) == 35 + 195 == 230

    assert len(
        broadcast_area_libraries.get_polygons_for_areas_lat_long(
            'countries-E92000001',
            'countries-S92000003',
        )
    ) == 35 + 195 == 230

    assert broadcast_area_libraries.get_polygons_for_areas_lat_long('countries-E92000001')[0][0] == [
        55.811085, -2.034358  # https://goo.gl/maps/wsf2LUWzYinwydMk8
    ]


def test_polygons_are_enclosed_unless_asked_not_to_be():
    england = broadcast_area_libraries.get('countries').get('countries-E92000001')

    assert len(england.polygons) == len(england.unenclosed_polygons)

    first_polygon = england.polygons[0]
    assert first_polygon[0] != first_polygon[1] != first_polygon[2]
    assert first_polygon[0] == first_polygon[-1]

    first_polygon_unenclosed = england.unenclosed_polygons[0]
    assert first_polygon_unenclosed[0] == first_polygon[0]
    assert first_polygon_unenclosed[-1] != first_polygon[-1]
    assert first_polygon_unenclosed[-1] == first_polygon[-2]


def test_lat_long_order():

    lat_long = broadcast_area_libraries.get_polygons_for_areas_lat_long('countries-E92000001')
    long_lat = broadcast_area_libraries.get_polygons_for_areas_long_lat('countries-E92000001')
    assert len(lat_long[0]) == len(long_lat[0]) == 2082  # Coordinates in polygon
    assert len(lat_long[0][0]) == len(long_lat[0][0]) == 2  # Axes in coordinates
    assert lat_long[0][0] == list(reversed(long_lat[0][0]))


def test_includes_electoral_wards():

    areas = broadcast_area_libraries.get_areas(['electoral-wards-of-the-united-kingdom-E05009289'])
    assert len(areas) == 1


def test_electoral_wards_are_groupable_cardiff():
    areas = broadcast_area_libraries.get_areas(['electoral-wards-of-the-united-kingdom-W06000015'])
    assert len(areas) == 1
    cardiff = areas[0]
    assert len(cardiff.sub_areas) == 29


def test_electoral_wards_are_groupable_ealing():
    areas = broadcast_area_libraries.get_areas(['electoral-wards-of-the-united-kingdom-E09000009'])
    assert len(areas) == 1
    ealing = areas[0]
    assert len(ealing.sub_areas) == 23


def test_repository_has_all_libraries():
    repo = BroadcastAreasRepository()
    libraries = repo.get_libraries()

    assert len(libraries) == 4
    assert [
        'Counties and Unitary Authorities in England and Wales',
        'Countries',
        'Electoral Wards of the United Kingdom',
        'Regions of England',
    ] == sorted([name for _, name, _is_group in libraries])
