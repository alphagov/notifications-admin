#!/usr/bin/env python

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
wards_filepath = source_files_path / "Electoral Wards May 2020.geojson"

# http://geoportal.statistics.gov.uk/datasets/ward-to-westminster-parliamentary-constituency-to-local-authority-district-december-2019-lookup-in-the-united-kingdom/data
las_filepath = source_files_path / "Electoral Wards and Local Authorities 2020.geojson"

ward_code_to_la_mapping = {
    f["properties"]["WD19CD"]: f["properties"]["LAD19NM"]
    for f in geojson.loads(las_filepath.read_text())["features"]
}
ward_code_to_la_id_mapping = {
    f["properties"]["WD19CD"]: f["properties"]["LAD19CD"]
    for f in geojson.loads(las_filepath.read_text())["features"]
}

dataset_name = "Local authorities"
dataset_name_singular = "local authority"
dataset_id = "wd20-lad20"
repo.insert_broadcast_area_library(
    dataset_id,
    name=dataset_name,
    name_singular=dataset_name_singular,
    is_group=True,
)

areas_to_add = []

for f in geojson.loads(wards_filepath.read_text())["features"]:
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
areas_to_add = []

las_filepath = source_files_path / "Local Authorities May 2020.geojson"

for feature in geojson.loads(las_filepath.read_text())["features"]:
    la_id = feature["properties"]["lad20cd"]
    group_name = feature["properties"]["lad20nm"]

    print()  # noqa: T001
    print(group_name)  # noqa: T001

    group_id = "lad20-" + la_id

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
