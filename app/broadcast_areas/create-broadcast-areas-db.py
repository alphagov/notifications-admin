#!/usr/bin/env python

import csv
import pickle
import sys
from math import isclose
from pathlib import Path

import geojson
from notifications_utils.formatters import formatted_list
from notifications_utils.polygons import Polygons
from populations import (
    BRYHER,
    CITY_OF_LONDON,
    MEDIAN_AGE_RANGE_UK,
    MEDIAN_AGE_UK,
    SMARTPHONE_OWNERSHIP_BY_AGE_RANGE,
    estimate_number_of_smartphones_for_population,
)
from repo import BroadcastAreasRepository, rtree_index_path
from rtreelib import Rect, RTree
from shapely import wkt
from shapely.geometry import MultiPolygon, Polygon

source_files_path = Path(__file__).resolve().parent / 'source_files'
point_counts = []
invalid_polygons = []
rtree_index = RTree()


def simplify_geometry(feature):
    if feature["type"] == "Polygon":
        return [feature["coordinates"][0]]
    elif feature["type"] == "MultiPolygon":
        return [polygon for polygon, *_holes in feature["coordinates"]]
    else:
        raise Exception("Unknown type: {}".format(feature["type"]))


def clean_up_invalid_polygons(polygons, indent="    "):
    for index, polygon in enumerate(polygons):
        shapely_polygon = Polygon(polygon)

        if shapely_polygon.is_valid:
            print(  # noqa: T001
                f"{indent}Polygon {index + 1}/{len(polygons)} is valid"
            )
            yield polygon

        else:
            invalid_polygons.append(shapely_polygon)

            # We’ve found polygons where all the points line up, so they
            # don’t have an area. They wouldn’t contribute to a broadcast
            # so we can ignore them.
            if shapely_polygon.area == 0:
                print(  # noqa: T001
                    f"{indent}Polygon {index + 1}/{len(polygons)} has 0 area, skipping"
                )
                continue

            print(  # noqa: T001
                f"{indent}Polygon {index + 1}/{len(polygons)} needs fixing..."
            )

            # The simplest kind of invalid polygon is one that has two
            # duplicate points in a row at a given precision, so the
            # first thing to try is removing those points using
            # simplification with a tolerance of 0
            polygon_with_duplicate_points_removed = wkt.loads(
                wkt.dumps(shapely_polygon, rounding_precision=5)
            ).simplify(0)

            if polygon_with_duplicate_points_removed.is_valid:
                yield polygon_with_duplicate_points_removed
                continue

            # Buffering with a size of 0 is a trick to make valid
            # geometries from polygons that self intersect
            buffered = shapely_polygon.buffer(0)

            # If the buffering has caused our polygon to split into
            # multiple polygons, we need to recursively check them
            # instead
            if isinstance(buffered, MultiPolygon):
                for sub_polygon in clean_up_invalid_polygons(buffered, indent="        "):
                    yield sub_polygon
                continue

            # We only care about the exterior of the polygon, not an
            # holes in it that may have been created by fixing self
            # intersection
            fixed_polygon = Polygon(buffered.exterior)

            # Make sure the polygon is now valid, and that we haven’t
            # drastically transformed the polygon by ‘fixing’ it
            assert fixed_polygon.is_valid
            assert isclose(fixed_polygon.area, polygon.area, rel_tol=0.001)

            print(  # noqa: T001
                f"{indent}Polygon {index + 1}/{len(polygons)} fixed!"
            )

            yield fixed_polygon


def polygons_and_simplified_polygons(feature):
    if keep_old_polygons:
        # cheat and shortcut out
        return [], []

    polygons = Polygons(simplify_geometry(feature))
    polygons = list(clean_up_invalid_polygons(polygons))
    polygons = Polygons(polygons)

    full_resolution = polygons.remove_too_small
    smoothed = full_resolution.smooth
    simplified = smoothed.simplify

    print(  # noqa: T001
        f'    Original:{full_resolution.point_count: >5} points'
        f'    Smoothed:{smoothed.point_count: >5} points'
        f'    Simplified:{simplified.point_count: >4} points'
    )

    point_counts.append(simplified.point_count)

    if simplified.point_count >= 200:
        raise RuntimeError(
            'Too many points '
            '(adjust Polygons.perimeter_to_simplification_ratio or '
            'Polygons.perimeter_to_buffer_ratio)'
        )

    return (
        full_resolution.as_coordinate_pairs_long_lat,
        simplified.as_coordinate_pairs_long_lat,
    )


def estimate_number_of_smartphones_in_area(country_or_ward_code):

    if country_or_ward_code in CITY_OF_LONDON.WARDS:
        # We don’t have population figures for wards of the City of
        # London. We’ll leave it empty here and estimate on the fly
        # later based on physical area.
        print('    Population:   N/A')  # noqa: T001
        return None

    # For some reason Bryher is the only ward missing population data, so we
    # need to hard code it. For simplicity, let’s assume all 84 people who
    # live on Bryher are 40 years old
    if country_or_ward_code == BRYHER.WD20_CODE:
        return BRYHER.POPULATION * SMARTPHONE_OWNERSHIP_BY_AGE_RANGE[MEDIAN_AGE_RANGE_UK]

    if country_or_ward_code not in area_to_population_mapping:
        raise ValueError(f'No population data for {country_or_ward_code}')

    return estimate_number_of_smartphones_for_population(
        area_to_population_mapping[country_or_ward_code]
    )


test_filepath = source_files_path / "Test.geojson"
demo_filepath = source_files_path / "Demo.geojson"
ctry19_filepath = source_files_path / "Countries.geojson"

# https://geoportal.statistics.gov.uk/datasets/wards-may-2020-boundaries-uk-bgc
# Converted to geojson manually from SHP because of GeoJSON download limits
wd20_filepath = source_files_path / "Electoral Wards May 2020.geojson"

# http://geoportal.statistics.gov.uk/datasets/local-authority-districts-may-2020-boundaries-uk-bgc
lad20_filepath = source_files_path / "Local Authorities May 2020.geojson"

# https://geoportal.statistics.gov.uk/datasets/counties-and-unitary-authorities-december-2019-boundaries-uk-bgc
ctyua19_filepath = source_files_path / "Counties_and_Unitary_Authorities__December_2019__Boundaries_UK_BGC.geojson"


# http://geoportal.statistics.gov.uk/datasets/ward-to-westminster-parliamentary-constituency-to-local-authority-district-december-2019-lookup-in-the-united-kingdom/data
wd_lad_map_filepath = source_files_path / "Electoral Wards and Local Authorities 2020.geojson"

# https://geoportal.statistics.gov.uk/datasets/lower-tier-local-authority-to-upper-tier-local-authority-december-2019-lookup-in-england-and-wales?where=LTLA19CD%20%3D%20%27E06000045%27
ltla_utla_map_filepath = source_files_path / "Lower_Tier_Local_Authority_to_Upper_Tier_Local_Authority__December_2019__Lookup_in_England_and_Wales.csv"  # noqa: E501

# https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/wardlevelmidyearpopulationestimatesexperimental
population_filepath_england_wales = source_files_path / "Mid-2019_Persons_England_Wales.csv"
# https://www.nrscotland.gov.uk/statistics-and-data/statistics/statistics-by-theme/population/population-estimates/2011-based-special-area-population-estimates/electoral-ward-population-estimates
population_filepath_scotland = source_files_path / "Mid-2019_Persons_Scotland.csv"
population_filepath_northern_ireland = source_files_path / "Ward-2014_Northern_Ireland.csv"
population_filepath_uk = source_files_path / "MYE1-2019.csv"


ward_code_to_la_mapping = {
    f["properties"]["WD19CD"]: f["properties"]["LAD19NM"]
    for f in geojson.loads(wd_lad_map_filepath.read_text())["features"]
}
ward_code_to_la_id_mapping = {
    f["properties"]["WD19CD"]: f["properties"]["LAD19CD"]
    for f in geojson.loads(wd_lad_map_filepath.read_text())["features"]
}


# the mapping dict is empty for lower tier local authorities that are also upper tier (unitary authorities, etc)
ltla_utla_mapping_csv = csv.DictReader(ltla_utla_map_filepath.open())
la_code_to_cty_id_mapping = {
    row['LTLA19CD']: row['UTLA19CD'] for row in ltla_utla_mapping_csv if row['LTLA19CD'] != row['UTLA19CD']
}

area_to_population_mapping = {}

for population_filepath in (
    population_filepath_uk,
    population_filepath_england_wales,
    population_filepath_northern_ireland,
    population_filepath_scotland,
):
    area_to_population_csv = csv.DictReader(population_filepath.open())
    for row in area_to_population_csv:
        area_to_population_mapping[row['ward']] = [
            (
                int(k) if k.isnumeric() else MEDIAN_AGE_UK,
                int(float(v.replace(',', '') or '0'))
            )
            for k, v in row.items() if k != 'ward'
        ]


def add_test_areas():
    dataset_id = 'test'
    dataset_geojson = geojson.loads(test_filepath.read_text())
    repo.insert_broadcast_area_library(
        dataset_id,
        name='Test areas',
        name_singular='test area',
        is_group=False,
    )

    areas_to_add = []
    for feature in dataset_geojson["features"]:
        f_id = feature["properties"]['id']
        f_name = feature["properties"]['name']

        print()  # noqa: T001
        print(f_name)  # noqa: T001

        feature, _ = polygons_and_simplified_polygons(
            feature["geometry"]
        )
        areas_to_add.append([
            f'{dataset_id}-{f_id}', f_name,
            dataset_id, None,
            feature, feature,
            0,
        ])

    repo.insert_broadcast_areas(areas_to_add, keep_old_polygons)


def add_demo_areas():
    dataset_id = 'demo'
    dataset_geojson = geojson.loads(demo_filepath.read_text())
    repo.insert_broadcast_area_library(
        dataset_id,
        name='Demo areas',
        name_singular='demo area',
        is_group=False,
    )

    areas_to_add = []
    for feature in dataset_geojson["features"]:
        f_id = feature["properties"]['id']
        f_name = feature["properties"]['name']
        f_count_of_phones = feature["properties"]['count_of_phones']

        print()  # noqa: T001
        print(f_name)  # noqa: T001

        feature, _ = polygons_and_simplified_polygons(
            feature["geometry"]
        )

        print('    Phones: ', f_count_of_phones)  # noqa: T001

        areas_to_add.append([
            f'{dataset_id}-{f_id}', f_name,
            dataset_id, None,
            feature, feature,
            f_count_of_phones,
        ])

    repo.insert_broadcast_areas(areas_to_add, keep_old_polygons)


def add_countries():
    dataset_id = 'ctry19'
    dataset_geojson = geojson.loads(ctry19_filepath.read_text())
    repo.insert_broadcast_area_library(
        'ctry19',
        name='Countries',
        name_singular='country',
        is_group=False,
    )

    areas_to_add = []
    for feature in dataset_geojson["features"]:
        f_id = feature["properties"]['ctry19cd']
        f_name = feature["properties"]['ctry19nm']

        print()  # noqa: T001
        print(f_name)  # noqa: T001

        feature, simple_feature = (
            polygons_and_simplified_polygons(feature["geometry"])
        )
        areas_to_add.append([
            f'ctry19-{f_id}', f_name,
            dataset_id, None,
            feature, simple_feature,
            estimate_number_of_smartphones_in_area(f_id),
        ])

    repo.insert_broadcast_areas(areas_to_add, keep_old_polygons)


def add_wards_local_authorities_and_counties():
    dataset_name = "Local authorities"
    dataset_name_singular = "local authority"
    dataset_id = "wd20-lad20-ctyua19"
    repo.insert_broadcast_area_library(
        dataset_id,
        name=dataset_name,
        name_singular=dataset_name_singular,
        is_group=True,
    )
    _add_electoral_wards(dataset_id)
    _add_local_authorities(dataset_id)
    _add_counties_and_unitary_authorities(dataset_id)


def _add_electoral_wards(dataset_id):
    areas_to_add = []

    for feature in geojson.loads(wd20_filepath.read_text())["features"]:
        ward_code = feature["properties"]["wd20cd"]
        ward_name = feature["properties"]["wd20nm"]
        ward_id = "wd20-" + ward_code

        print()  # noqa: T001
        print(ward_name)  # noqa: T001

        try:
            la_id = "lad20-" + ward_code_to_la_id_mapping[ward_code]

            feature, simple_feature = (
                polygons_and_simplified_polygons(feature["geometry"])
            )

            if feature:
                rtree_index.insert(ward_id, Rect(*Polygons(feature).bounds))

            areas_to_add.append([
                ward_id, ward_name,
                dataset_id, la_id,
                feature, simple_feature,
                estimate_number_of_smartphones_in_area(ward_code),
            ])

        except KeyError:
            print("Skipping", ward_code, ward_name)  # noqa: T001

    rtree_index_path.open('wb').write(pickle.dumps(rtree_index))
    repo.insert_broadcast_areas(areas_to_add, keep_old_polygons)


def _add_local_authorities(dataset_id):
    areas_to_add = []

    for feature in geojson.loads(lad20_filepath.read_text())["features"]:
        la_id = feature["properties"]["LAD20CD"]
        group_name = feature["properties"]["LAD20NM"]

        print()  # noqa: T001
        print(group_name)  # noqa: T001

        group_id = "lad20-" + la_id

        feature, simple_feature = (
            polygons_and_simplified_polygons(feature["geometry"])
        )

        ctyua_id = la_code_to_cty_id_mapping.get(la_id)
        areas_to_add.append([
            group_id,
            group_name,
            dataset_id,
            'ctyua19-' + ctyua_id if ctyua_id else None,
            feature,
            simple_feature,
            None,
        ])
    repo.insert_broadcast_areas(areas_to_add, keep_old_polygons)


# counties and unitary authorities
def _add_counties_and_unitary_authorities(dataset_id):
    areas_to_add = []
    for feature in geojson.loads(ctyua19_filepath.read_text())['features']:
        ctyua_id = feature["properties"]["ctyua19cd"]
        group_name = feature["properties"]["ctyua19nm"]

        la_id = 'lad20-' + ctyua_id
        if repo.get_areas([la_id]):
            continue

        group_id = "ctyua19-" + ctyua_id

        feature, simple_feature = (
            polygons_and_simplified_polygons(feature["geometry"])
        )

        areas_to_add.append([
            group_id, group_name,
            dataset_id, None,
            feature, simple_feature,
            None,
        ])

    repo.insert_broadcast_areas(areas_to_add, keep_old_polygons)


# cheeky global variable
keep_old_polygons = sys.argv[1:] == ['--keep-old-polygons']
print('keep_old_polygons: ', keep_old_polygons)  # noqa: T001

repo = BroadcastAreasRepository()

if keep_old_polygons:
    repo.delete_library_data()
else:
    repo.delete_db()
    repo.create_tables()
add_test_areas()
add_demo_areas()
add_countries()
add_wards_local_authorities_and_counties()

most_detailed_polygons = formatted_list(
    sorted(point_counts, reverse=True)[:5],
    before_each='',
    after_each='',
)

print(  # noqa: T001
    '\n'
    'DONE\n'
    f'    Processed {len(point_counts):,} polygons.\n'
    f'    Cleaned up {len(invalid_polygons):,} polygons.\n'
    f'    Highest point counts once simplifed: {most_detailed_polygons}\n'
)
