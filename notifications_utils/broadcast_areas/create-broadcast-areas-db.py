#!/usr/bin/env python

import geojson
from pathlib import Path

from repo import BroadcastAreasRepository

package_path = Path(__file__).resolve().parent

repo = BroadcastAreasRepository()

repo.delete_db()
repo.create_tables()

simple_datasets = [
    ("Countries", "ctry19nm"),
    ("Regions of England", "rgn18nm"),
    ("Counties and Unitary Authorities in England and Wales", "ctyua16nm"),
]
for dataset_name, name_field in simple_datasets:
    filepath = package_path / "{}.geojson".format(dataset_name)
    dataset_geojson = geojson.loads(filepath.read_text())

    repo.insert_broadcast_area_library(dataset_name)

    for feature in dataset_geojson["features"]:
        f_name = feature["properties"][name_field]
        repo.insert_broadcast_areas([[f_name, dataset_name, feature]])

# https://geoportal.statistics.gov.uk/datasets/wards-may-2020-boundaries-uk-bgc
# Converted to geojson manually from SHP because of GeoJSON download limits
wards_filepath = package_path / "Electoral Wards May 2020.geojson"

# http://geoportal.statistics.gov.uk/datasets/ward-to-westminster-parliamentary-constituency-to-local-authority-district-december-2019-lookup-in-the-united-kingdom/data
las_filepath = package_path / "Electoral Wards and Local Authorities 2020.geojson"

ward_code_to_la_mapping = {
    f["properties"]["WD19CD"]: f["properties"]["LAD19NM"]
    for f in geojson.loads(las_filepath.read_text())["features"]
}

dataset_name = "Electoral Wards of the United Kingdom"
repo.insert_broadcast_area_library(dataset_name)

areas_to_add = []

for f in geojson.loads(wards_filepath.read_text())["features"]:

    ward_code = f["properties"]["wd20cd"]
    ward_name = f["properties"]["wd20nm"]

    try:
        la_name = ward_code_to_la_mapping[ward_code]

        f_name = "{} - {}".format(la_name, ward_name)
        areas_to_add.append([f_name, dataset_name, f])

    except KeyError:
        print("Skipping", ward_code, ward_name)  # noqa: T001

repo.insert_broadcast_areas(areas_to_add)
