#!/usr/bin/env python

from copy import deepcopy
import geojson
from pathlib import Path
import shapely.geometry as sgeom

from repo import BroadcastAreasRepository

package_path = Path(__file__).resolve().parent


def simplify_polygon(series):
    polygon, *_holes = series  # discard holes

    approx_metres_to_degree = 111320
    desired_resolution_metres = 10
    simplify_degrees = desired_resolution_metres / approx_metres_to_degree

    simplified_polygon = None
    num_polys = len(polygon)
    while True:
        simplified_polygon = sgeom.LineString(polygon)
        simplified_polygon = simplified_polygon.buffer(simplify_degrees)
        simplified_polygon = simplified_polygon.simplify(simplify_degrees)
        simplified_polygon = [[c[0], c[1]] for c in simplified_polygon.exterior.coords]

        num_polys = len(simplified_polygon)
        simplify_degrees *= 1.5
        if num_polys <= 125:
            break

    return [simplified_polygon]


def simplify_geometry(feature):
    if feature["type"] == "Polygon":
        feature["coordinates"] = simplify_polygon(feature["coordinates"])
        return feature
    elif feature["type"] == "MultiPolygon":
        feature["coordinates"] = [
            simplify_polygon(polygon)
            for polygon in feature["coordinates"]
        ]
        return feature
    else:
        raise Exception("Unknown type: {}".format(feature["type"]))


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

        simple_feature = deepcopy(feature)
        simple_feature["geometry"] = simplify_geometry(simple_feature["geometry"])
        repo.insert_broadcast_areas([[f_name, dataset_name, feature, simple_feature]])

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

        sf = deepcopy(f)
        sf["geometry"] = simplify_geometry(sf["geometry"])

        areas_to_add.append([f_name, dataset_name, f, sf])

    except KeyError:
        print("Skipping", ward_code, ward_name)  # noqa: T001

repo.insert_broadcast_areas(areas_to_add)
