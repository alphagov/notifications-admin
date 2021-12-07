from math import isclose

import pytest
from custom_polygons import BRISTOL, SKYE

from app.broadcast_areas.models import (
    BroadcastAreasRepository,
    CustomBroadcastArea,
    broadcast_area_libraries,
)
from app.broadcast_areas.populations import (
    CITY_OF_LONDON,
    estimate_number_of_smartphones_for_population,
)


def close_enough(a, b):
    return isclose(a, b, rel_tol=0.001)  # Within 0.1% difference


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
            'demo',
            'Demo areas',
            False,
        ),
        (
            'wd20-lad20-ctyua19',
            'Local authorities',
            True,
        ),
        (
            'test',
            'Test areas',
            False,
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
        broadcast_area_libraries.get_areas([id])[0]
    )


def test_get_names_of_areas():
    areas = broadcast_area_libraries.get_areas([
        'ctry19-W92000004',
        'lad20-W06000014',
        'ctry19-E92000001',
    ])
    assert [area.name for area in sorted(areas)] == [
        'England', 'Vale of Glamorgan', 'Wales',
    ]


def test_has_polygons():

    england = broadcast_area_libraries.get_areas(['ctry19-E92000001'])[0]
    scotland = broadcast_area_libraries.get_areas(['ctry19-S92000003'])[0]

    assert len(england.polygons) == 35
    assert len(scotland.polygons) == 195

    assert england.polygons.as_coordinate_pairs_lat_long[0][0] == [
        55.81108, -2.03436  # https://goo.gl/maps/HMFHGogohXdh9ggo8
    ]


def test_polygons_are_enclosed():
    england = broadcast_area_libraries.get('ctry19').get('ctry19-E92000001')

    first_polygon = england.polygons.as_coordinate_pairs_lat_long[0]
    assert first_polygon[0] != first_polygon[1] != first_polygon[2]
    assert first_polygon[0] == first_polygon[-1]


def test_lat_long_order():

    england = broadcast_area_libraries.get_areas(['ctry19-E92000001'])[0]

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

    assert len(libraries) == 4
    assert [
        ('Countries', 'country'),
        ('Demo areas', 'demo area'),
        ('Test areas', 'test area'),
        ('Local authorities', 'local authority'),
    ] == [(name, name_singular) for _, name, name_singular, _is_group in libraries]


@pytest.mark.parametrize('library', (
    broadcast_area_libraries
))
def test_every_area_has_count_of_phones(library):
    for area in library:
        if library.id == 'test':
            assert area.count_of_phones == 0
        else:
            assert area.count_of_phones > 0


@pytest.mark.parametrize('area_id, area_name, expected_count', (

    # Unitary authority
    ('ctyua19-E10000014', 'Hampshire', 853_594.48),

    # District
    ('lad20-E07000087', 'Fareham', 81_970.06),

    # Ward
    ('wd20-E05004516', 'Fareham East', 5_684.9),

    # Unitary authority
    ('lad20-E09000012', 'Hackney', 222_578.0),

    # Ward
    ('wd20-E05009373', 'Hackney Downs', 11_321.169999999998),

    # Special case: ward with hard-coded population
    ('wd20-E05011090', 'Bryher', 76.44),

    # Areas with missing data
    ('lad20-E07000008', 'Cambridge', 0),
    ('lad20-E07000084', 'Basingstoke and Deane', 0),
    ('lad20-E07000118', 'Chorley', 0),
    ('lad20-E07000178', 'Oxford', 0),

))
def test_count_of_phones_for_all_levels(area_id, area_name, expected_count):
    area = broadcast_area_libraries.get_areas([area_id])[0]
    assert area.name == area_name
    assert area.count_of_phones == expected_count


def test_city_of_london_counts_are_not_derived_from_population():
    city_of_london = broadcast_area_libraries.get_areas(['lad20-E09000001'])[0]

    assert city_of_london.name == 'City of London'
    assert len(city_of_london.sub_areas) == len(CITY_OF_LONDON.WARDS) == 25

    for ward in city_of_london.sub_areas:
        # The population of the whole City of London is 9,401, so an
        # average of 300 per ward. What we’re asserting here is that the
        # count of phones is much larger, because it isn’t derived from
        # the resident population.
        assert ward.count_of_phones > 5_000


@pytest.mark.parametrize('population, expected_estimate', (
    # Upper and lower bounds of each age range
    (
        [(0, 100)], 50,
    ),
    (
        [(16, 100)], 100
    ),
    (
        [(24, 100)], 100,
    ),
    (
        [(25, 100)], 97,
    ),
    (
        [(34, 100)], 97,
    ),
    (
        [(35, 100)], 91
    ),
    (
        [(44, 100)], 91,
    ),
    (
        [(45, 100)], 88
    ),
    (
        [(54, 100)], 88,
    ),
    (
        [(55, 100)], 73
    ),
    (
        [(64, 100)], 73,
    ),
    (
        [(65, 100)], 40
    ),
    (
        [(999, 100)], 40,
    ),
    # Multiple different ages in a single popualtion
    (
        [(16, 100), (54, 100)], 188
    ),
    (
        [(1, 1000), (66, 100)], 540
    ),
))
def test_estimate_number_of_smartphones_for_population(
    population, expected_estimate,
):
    assert estimate_number_of_smartphones_for_population(
        population
    ) == expected_estimate


@pytest.mark.parametrize('area, expected_phones_per_square_mile', (
    (
        # Islington (most dense in UK)
        'lad20-E09000019', 32_662
    ),
    (
        # Cordwainer Ward (City of London)
        # This is higher than Islington because we inflate the
        # popualtion to account for daytime workers
        'wd20-E05009300', 392_870
    ),
    (
        # Crewe East
        'wd20-E05008621', 3_289),
    (
        # Eden (Cumbria, least dense in England)
        'lad20-E07000030', 43.41
    ),
    (
        # Highland (least dense in UK)
        'lad20-S12000017', 6.97
    ),
))
def test_phone_density(
    area, expected_phones_per_square_mile,
):
    assert close_enough(
        broadcast_area_libraries.get_areas([area])[0].phone_density,
        expected_phones_per_square_mile,
    )


@pytest.mark.parametrize('area, expected_bleed_in_m', (
    (
        # Islington (most dense in UK)
        'lad20-E09000019', 500
    ),
    (
        # Cordwainer Ward (City of London)
        # Special case because of inflated daytime population
        'wd20-E05009300', 500
    ),
    (
        # Crewe East
        'wd20-E05008621', 1_504
    ),
    (
        # Eden (Cumbria, least dense in England)
        'lad20-E07000030', 3_852
    ),
    (
        # Highland (least dense in UK)
        'lad20-S12000017', 4_846
    ),
    (
        # No population data available
        'test-santa-claus-village-rovaniemi-a', 1_500
    )
))
def test_estimated_bleed(
    area, expected_bleed_in_m
):
    assert close_enough(
        broadcast_area_libraries.get_areas([area])[0].estimated_bleed_in_m,
        expected_bleed_in_m,
    )


@pytest.mark.parametrize('polygon, expected_possible_overlaps, expected_count_of_phones', (
    (
        BRISTOL,
        [
            'Ashley',
            'Bedminster',
            'Central',
            'Clifton',
            'Clifton Down',
            'Cotham',
            'Hotwells and Harbourside',
            'Knowle',
            'Lawrence Hill',
            'Southville',
            'Stoke Bishop',
            'Windmill Hill',
        ],
        72_817,
    ),
    (
        SKYE,
        [
            'Caol and Mallaig',
            'Eilean á Chèo',
            'Na Hearadh agus Ceann a Deas nan Loch',
            'Wester Ross, Strathpeffer and Lochalsh',
        ],
        3_413,
    ),
))
def test_count_of_phones_for_custom_area(
    polygon,
    expected_possible_overlaps,
    expected_count_of_phones,
):
    area = CustomBroadcastArea(
        name='Example',
        polygons=[polygon],
    )

    assert sorted(
        overlap.name for overlap in area.nearby_electoral_wards
    ) == expected_possible_overlaps

    assert close_enough(area.count_of_phones, expected_count_of_phones)
