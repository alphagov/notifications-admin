#!/usr/bin/env python

import csv
from copy import deepcopy
from pathlib import Path

import geojson
from notifications_utils.formatters import formatted_list

from polygons import Polygons
from repo import BroadcastAreasRepository

source_files_path = Path(__file__).resolve().parent / 'source_files'
point_counts = []


def simplify_geometry(feature):
    if feature["type"] == "Polygon":
        return [feature["coordinates"][0]]
    elif feature["type"] == "MultiPolygon":
        return [polygon for polygon, *_holes in feature["coordinates"]]
    else:
        raise Exception("Unknown type: {}".format(feature["type"]))


def polygons_and_simplified_polygons(feature):

    polygons = Polygons(simplify_geometry(feature))
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


repo = BroadcastAreasRepository()

repo.delete_db()
repo.create_tables()

simple_datasets = [
    ("Countries", "country", "ctry19cd", "ctry19nm"),
]
for dataset_name, dataset_name_singular, id_field, name_field in simple_datasets:
    filepath = source_files_path / "{}.geojson".format(dataset_name)

    dataset_id = id_field[:-2]
    dataset_geojson = geojson.loads(filepath.read_text())

    repo.insert_broadcast_area_library(
        dataset_id,
        name=dataset_name,
        name_singular=dataset_name_singular,
        is_group=False,
    )

    for feature in dataset_geojson["features"]:
        f_id = dataset_id + "-" + feature["properties"][id_field]
        f_name = feature["properties"][name_field]

        print()  # noqa: T001
        print(f_name)  # noqa: T001

        feature, simple_feature = (
            polygons_and_simplified_polygons(feature["geometry"])
        )

        repo.insert_broadcast_areas([[
            f_id, f_name,
            dataset_id, None,
            feature, simple_feature,
        ]])

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


dataset_name = "Local authorities"
dataset_name_singular = "local authority"
dataset_id = "wd20-lad20-ctyua19"
repo.insert_broadcast_area_library(
    dataset_id,
    name=dataset_name,
    name_singular=dataset_name_singular,
    is_group=True,
)


# electoral wards

areas_to_add = []

for f in geojson.loads(wd20_filepath.read_text())["features"]:
    ward_code = f["properties"]["wd20cd"]
    ward_name = f["properties"]["wd20nm"]
    ward_id = "wd20-" + ward_code

    print()  # noqa: T001
    print(ward_name)  # noqa: T001

    try:
        la_id = "lad20-" + ward_code_to_la_id_mapping[ward_code]
        la_name = ward_code_to_la_mapping[ward_code]

        feature, simple_feature = (
            polygons_and_simplified_polygons(f["geometry"])
        )

        areas_to_add.append([
            ward_id, ward_name,
            dataset_id, la_id,
            feature, simple_feature
        ])

    except KeyError:
        print("Skipping", ward_code, ward_name)  # noqa: T001

repo.insert_broadcast_areas(areas_to_add)


# local authorities

areas_to_add = []

for feature in geojson.loads(lad20_filepath.read_text())["features"]:
    la_id = feature["properties"]["lad20cd"]
    group_name = feature["properties"]["lad20nm"]

    print()  # noqa: T001
    print(group_name)  # noqa: T001

    group_id = "lad20-" + la_id

    feature, simple_feature = (
        polygons_and_simplified_polygons(feature["geometry"])
    )

    ctyua_id = la_code_to_cty_id_mapping.get(la_id)
    if ctyua_id:
        print(f'{group_id} {group_name} is part of {ctyua_id}')  # noqa: T001
    areas_to_add.append([
        group_id,
        group_name,
        dataset_id,
        'ctyua19-' + ctyua_id if ctyua_id else None,
        feature,
        simple_feature
    ])
repo.insert_broadcast_areas(areas_to_add)


# counties and unitary authorities

areas_to_add = []
for feature in geojson.loads(ctyua19_filepath.read_text())['features']:
    ctyua_id = feature["properties"]["ctyua19cd"]
    group_name = feature["properties"]["ctyua19nm"]

    print('County/Unitary Authority', group_name)  # noqa: T001

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
        feature, simple_feature
    ])

repo.insert_broadcast_areas(areas_to_add)


most_detailed_polygons = formatted_list(
    sorted(point_counts, reverse=True)[:5],
    before_each='',
    after_each='',
)
print(  # noqa: T001
    '\n'
    'DONE\n'
    f'    Processed {len(point_counts):,} polygons.\n'
    f'    Highest point counts once simplifed: {most_detailed_polygons}\n'
)
