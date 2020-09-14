import pytest

from app.broadcast_areas import (
    BroadcastAreasRepository,
    broadcast_area_libraries,
)


def test_loads_libraries():
    assert [
        (library.id, library.name, library.is_group) for library in sorted(broadcast_area_libraries)
    ] == [
        (
            'ctry19',
            'Countries',
            False,
        ),
        (
            'wd20-lad20-ctyua19',
            'Local authorities',
            True,
        ),
    ]


def test_loads_areas_from_library():
    assert [
        (area.id, area.name) for area in sorted(
            broadcast_area_libraries.get('ctry19')
        )
    ] == [
        ('ctry19-E92000001', 'England'),
        ('ctry19-N92000002', 'Northern Ireland'),
        ('ctry19-S92000003', 'Scotland'),
        ('ctry19-W92000004', 'Wales'),
    ]


def test_examples():
    countries = broadcast_area_libraries.get('ctry19').get_examples()
    assert countries == 'England, Northern Ireland, Scotland and Wales'

    wards = broadcast_area_libraries.get('wd20-lad20-ctyua19').get_examples()
    assert wards == 'Aberdeen City, Aberdeenshire, Adur and 391 more…'


@pytest.mark.parametrize('id', (
    'ctry19-E92000001',
    'ctry19-N92000002',
    'ctry19-S92000003',
    'ctry19-W92000004',
    pytest.param('mercia', marks=pytest.mark.xfail(raises=KeyError)),
))
def test_loads_areas_from_libraries(id):
    assert (
        broadcast_area_libraries.get('ctry19').get(id)
    ) == (
        broadcast_area_libraries.get_areas(id)[0]
    )


def test_get_names_of_areas():
    areas = broadcast_area_libraries.get_areas(
        'ctry19-W92000004',
        'lad20-W06000014',
        'ctry19-E92000001',
    )
    assert [area.name for area in sorted(areas)] == [
        'England', 'Vale of Glamorgan', 'Wales',
    ]


def test_get_areas_accepts_lists():
    areas_from_list = broadcast_area_libraries.get_areas(
        [
            'ctry19-W92000004',
            'ctry19-E92000001',
        ]
    )
    areas_from_args = broadcast_area_libraries.get_areas(
        'ctry19-W92000004',
        'ctry19-E92000001',
    )
    assert len(areas_from_args) == len(areas_from_list) == 2
    assert areas_from_args == areas_from_list


def test_has_polygons():

    england = broadcast_area_libraries.get_areas('ctry19-E92000001')[0]
    scotland = broadcast_area_libraries.get_areas('ctry19-S92000003')[0]

    assert len(england.polygons) == 35
    assert len(scotland.polygons) == 195

    assert england.polygons.as_coordinate_pairs_lat_long[0][0] == [
        55.811085, -2.034358  # https://goo.gl/maps/wsf2LUWzYinwydMk8
    ]


def test_polygons_are_enclosed():
    england = broadcast_area_libraries.get('ctry19').get('ctry19-E92000001')

    first_polygon = england.polygons.as_coordinate_pairs_lat_long[0]
    assert first_polygon[0] != first_polygon[1] != first_polygon[2]
    assert first_polygon[0] == first_polygon[-1]


def test_lat_long_order():

    england = broadcast_area_libraries.get_areas('ctry19-E92000001')[0]

    lat_long = england.polygons.as_coordinate_pairs_lat_long
    long_lat = england.polygons.as_coordinate_pairs_long_lat

    assert len(lat_long[0]) == len(long_lat[0]) == 2082  # Coordinates in polygon
    assert len(lat_long[0][0]) == len(long_lat[0][0]) == 2  # Axes in coordinates
    assert lat_long[0][0] == list(reversed(long_lat[0][0]))


def test_includes_electoral_wards():

    areas = broadcast_area_libraries.get_areas(['wd20-E05009289'])
    assert len(areas) == 1


def test_electoral_wards_are_groupable_cardiff():
    areas = broadcast_area_libraries.get_areas(['lad20-W06000015'])
    assert len(areas) == 1
    cardiff = areas[0]
    assert len(cardiff.sub_areas) == 29


def test_electoral_wards_are_groupable_ealing():
    areas = broadcast_area_libraries.get_areas(['lad20-E09000009'])
    assert len(areas) == 1
    ealing = areas[0]
    assert len(ealing.sub_areas) == 23


def test_repository_has_all_libraries():
    repo = BroadcastAreasRepository()
    libraries = repo.get_libraries()

    assert len(libraries) == 2
    assert [
        ('Countries', 'country'),
        ('Local authorities', 'local authority'),
    ] == [(name, name_singular) for _, name, name_singular, _is_group in libraries]
