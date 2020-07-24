#!/usr/bin/env python

import geojson
from pathlib import Path

package_path = Path(__file__).resolve().parent

db_filepath = package_path / "broadcast-areas.sqlite3"
os.remove(str(db_filepath))
conn = sqlite3.connect(str(db_filepath))
conn.execute("""
CREATE TABLE broadcast_areas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    dataset TEXT NOT NULL,
    feature_geojson TEXT NOT NULL
)""")
conn.execute("""
CREATE INDEX broadcast_areas_dataset
ON broadcast_areas (dataset);
""")
conn.commit()

simple_datasets = [
    ("Countries", "ctry19nm"),
    ("Regions of England", "rgn18nm"),
    ("Counties and Unitary Authorities in England and Wales", "ctyua16nm"),
]
for dataset_name, name_field in simple_datasets:
    filepath = package_path / "{}.geojson".format(dataset_name)
    dataset_geojson = geojson.loads(filepath.read_text())

    q = """
    INSERT INTO broadcast_areas (id, name, dataset, feature_geojson)
    VALUES (?, ?, ?, ?)
    """

    for feature in dataset_geojson["features"]:
        f_name = feature["properties"][name_field]
        f_id = make_string_safe_for_id(f_name)
        conn.execute(q, (f_id, f_name, dataset_name, geojson.dumps(feature)))

    conn.commit()

# https://geoportal.statistics.gov.uk/datasets/wards-may-2020-boundaries-uk-bgc
# Converted to geojson manually from SHP because of GeoJSON download limits
wards_filepath = package_path / "Electoral Wards May 2020.geojson"

# http://geoportal.statistics.gov.uk/datasets/ward-to-westminster-parliamentary-constituency-to-local-authority-district-december-2019-lookup-in-the-united-kingdom/data
las_filepath = package_path / "Electoral Wards and Local Authorities 2020.geojson"

ward_code_to_la_mapping = {
    f["properties"]["WD19CD"]: f["properties"]["LAD19NM"]
    for f in geojson.loads(las_filepath.read_text())["features"]
}

for f in geojson.loads(wards_filepath.read_text())["features"]:
    dataset_name = "Electoral Wards of the United Kingdom"

    ward_code = f["properties"]["wd20cd"]
    ward_name = f["properties"]["wd20nm"]

    try:
        la_name = ward_code_to_la_mapping[ward_code]

        f_name = "{} - {}".format(la_name, ward_name)
        f_id = make_string_safe_for_id(f_name)

        q = """
        INSERT INTO broadcast_areas (id, name, dataset, feature_geojson)
        VALUES (?, ?, ?, ?)
        """
        conn.execute(q, (f_id, f_name, dataset_name, geojson.dumps(f)))

    except KeyError:
        print("Skipping", ward_code, ward_name)  # noqa: T001

conn.commit()
