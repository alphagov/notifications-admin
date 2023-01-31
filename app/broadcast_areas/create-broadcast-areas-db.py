#!/usr/bin/env python

import csv
import pickle
import sys
from math import isclose
from pathlib import Path

import geojson
from emergency_alerts_utils.formatters import formatted_list
from emergency_alerts_utils.polygons import Polygons
from populations import (
    BRYHER,
    CITY_OF_LONDON,
    MEDIAN_AGE_RANGE_UK,
    MEDIAN_AGE_UK,
    POLICE_FORCE_AREAS,
    SMARTPHONE_OWNERSHIP_BY_AGE_RANGE,
    estimate_number_of_smartphones_for_population,
)
from repo import BroadcastAreasRepository, rtree_index_path
from rtreelib import Rect, RTree
from shapely import wkt
from shapely.geometry import MultiPolygon, Polygon

source_files_path = Path(__file__).resolve().parent / "source_files"
point_counts = []
invalid_polygons = []
rtree_index = RTree()

# The hard limit in the CBCs is 6,000 points per polygon. But we also
# care about optimising how quickjly we can process and display polygons
# so we aim for something lower, i.e. enough to give us a good amount of
# precision relative to the accuracy of a cell broadcast
MAX_NUMBER_OF_POINTS_PER_POLYGON = 250


def simplify_geometry(feature):
    if feature["type"] == "Polygon":
        return [feature["coordinates"][0]]
    elif feature["type"] == "MultiPolygon":
        return [polygon for polygon, *_holes in feature["coordinates"]]
    else:
        raise Exception("Unknown type: {}".format(feature["type"]))


def clean_up_invalid_polygons(polygons, indent="    "):
    """
    This function expects a list of lists of coordinates defined in degrees
    """
    for index, polygon in enumerate(polygons):
        shapely_polygon = Polygon(polygon)

        # Some of our data has points which are incredibly close
        # together. In some cases they are close enough to be duplicates
        # at a given precision, which makes an invalid topology. In
        # other cases they are close enough that, when converting from
        # one coordinate system to another, they shift about enough to
        # create self-intersection. The fix in both cases is to reduce
        # the precision of the coordinates and then apply simplification
        # with a tolerance of 0.
        simplified_polygon = wkt.loads(
            wkt.dumps(shapely_polygon, rounding_precision=Polygons.output_precision_in_decimal_places - 1)
        ).simplify(0)

        if simplified_polygon.is_valid:
            print(f"{indent}Polygon {index + 1}/{len(polygons)} is valid")  # noqa: T201
            yield simplified_polygon

        else:
            invalid_polygons.append(shapely_polygon)

            # We’ve found polygons where all the points line up, so they
            # don’t have an area. They wouldn’t contribute to a broadcast
            # so we can ignore them.
            if simplified_polygon.area == 0:
                print(f"{indent}Polygon {index + 1}/{len(polygons)} has 0 area, skipping")  # noqa: T201
                continue

            print(f"{indent}Polygon {index + 1}/{len(polygons)} needs fixing...")  # noqa: T201

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
            assert isclose(fixed_polygon.area, shapely_polygon.area, rel_tol=0.001)

            print(f"{indent}Polygon {index + 1}/{len(polygons)} fixed!")  # noqa: T201

            yield fixed_polygon


def polygons_and_simplified_polygons(feature):
    if keep_old_polygons:
        # cheat and shortcut out
        return [], []

    raw_polygons = simplify_geometry(feature)
    clean_raw_polygons = [
        [[x, y] for x, y in polygon.exterior.coords] for polygon in clean_up_invalid_polygons(raw_polygons)
    ]
    polygons = Polygons(clean_raw_polygons)

    full_resolution = polygons.remove_too_small
    smoothed = full_resolution.smooth
    simplified = smoothed.simplify

    if not (len(full_resolution) or len(simplified)):
        raise RuntimeError("Polygon of 0 size found")

    print(  # noqa: T201
        f"    Original:{full_resolution.point_count: >5} points"
        f"    Smoothed:{smoothed.point_count: >5} points"
        f"    Simplified:{simplified.point_count: >4} points"
    )

    point_counts.append(simplified.point_count)

    if simplified.point_count >= MAX_NUMBER_OF_POINTS_PER_POLYGON:
        raise RuntimeError(
            "Too many points "
            "(adjust Polygons.perimeter_to_simplification_ratio or "
            "Polygons.perimeter_to_buffer_ratio)"
        )

    output = [
        full_resolution.as_coordinate_pairs_long_lat,
        simplified.as_coordinate_pairs_long_lat,
    ]

    # Check that the simplification process hasn’t introduced bad data
    for dataset in output:
        for polygon in dataset:
            assert Polygon(polygon).is_valid

    return output + [simplified.utm_crs]


def estimate_number_of_smartphones_in_area(country_or_ward_code):

    if country_or_ward_code in CITY_OF_LONDON.WARDS:
        # We don’t have population figures for wards of the City of
        # London. We’ll leave it empty here and estimate on the fly
        # later based on physical area.
        print("    Population:   N/A")  # noqa: T201
        return None

    # For some reason Bryher is the only ward missing population data, so we
    # need to hard code it. For simplicity, let’s assume all 84 people who
    # live on Bryher are 40 years old
    if country_or_ward_code == BRYHER.WD21_CODE:
        return BRYHER.POPULATION * SMARTPHONE_OWNERSHIP_BY_AGE_RANGE[MEDIAN_AGE_RANGE_UK]

    if country_or_ward_code not in area_to_population_mapping:
        raise ValueError(f"No population data for {country_or_ward_code}")

    return estimate_number_of_smartphones_for_population(area_to_population_mapping[country_or_ward_code])


test_filepath = source_files_path / "Test.geojson"

additional_filepath = source_files_path / "Additional.geojson"

ctry19_filepath = source_files_path / "Countries.geojson"

# https://geoportal.statistics.gov.uk/datasets/ons::wards-december-2021-uk-bgc
wd21_filepath = source_files_path / "Wards_(December_2021)_UK_BGC.geojson"

# https://geoportal.statistics.gov.uk/datasets/ons::local-authority-districts-december-2021-uk-bgc
lad21_filepath = source_files_path / "Local_Authority_Districts_(December_2021)_UK_BGC.geojson"

# https://geoportal.statistics.gov.uk/datasets/ons::counties-and-unitary-authorities-december-2021-uk-bgc
ctyua21_filepath = source_files_path / "Counties_and_Unitary_Authorities_(December_2021)_UK_BGC.geojson"

# https://geoportal.statistics.gov.uk/datasets/ons::police-force-areas-december-2020-ew-bgc
pfa20_filepath = source_files_path / "Police_Force_Areas_(December_2020)_EW_BGC.geojson"

# https://geoportal.statistics.gov.uk/documents/ward-to-local-authority-district-december-2021-lookup-in-the-united-kingdom/about
wd_lad_map_filepath = source_files_path / "WD21_LAD21_UK_LU.csv"

# https://geoportal.statistics.gov.uk/datasets/ons::lower-tier-local-authority-to-upper-tier-local-authority-april-2021-lookup-in-england-and-wales/explore
ltla_utla_map_filepath = (
    source_files_path
    / "Lower_Tier_Local_Authority_to_Upper_Tier_Local_Authority__April_2021__Lookup_in_England_and_Wales.csv"
)  # noqa: E501

# https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/wardlevelmidyearpopulationestimatesexperimental/mid2020sape23dt8a/wards210120popest.zip
# Munged using https://docs.google.com/spreadsheets/d/1gR50P0l02Fz7ZH7EwZI87F3axDbNp6oIDDnkKYgWEpA/edit#gid=2092678703
population_filepath_england_wales = source_files_path / "Mid-2020_Persons_England_Wales_(2021_wards).csv"

# https://www.nrscotland.gov.uk/statistics-and-data/statistics/statistics-by-theme/population/population-estimates/2011-based-special-area-population-estimates/electoral-ward-population-estimates
population_filepath_scotland = source_files_path / "Mid-2019_Persons_Scotland.csv"
population_filepath_northern_ireland = source_files_path / "Ward-2014_Northern_Ireland.csv"
population_filepath_uk = source_files_path / "MYE1-2019.csv"


ward_code_to_la_mapping = {row["WD21CD"]: row["LAD21NM"] for row in csv.DictReader(wd_lad_map_filepath.open())}
ward_code_to_la_id_mapping = {row["WD21CD"]: row["LAD21CD"] for row in csv.DictReader(wd_lad_map_filepath.open())}


# the mapping dict is empty for lower tier local authorities that are also upper tier (unitary authorities, etc)
ltla_utla_mapping_csv = csv.DictReader(ltla_utla_map_filepath.open())
la_code_to_cty_id_mapping = {
    row["LTLA21CD"]: row["UTLA21CD"] for row in ltla_utla_mapping_csv if row["LTLA21CD"] != row["UTLA21CD"]
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
        area_to_population_mapping[row["ward"]] = [
            (int(k) if k.isnumeric() else MEDIAN_AGE_UK, int(float(v.replace(",", "") or "0")))
            for k, v in row.items()
            if k != "ward"
        ]


def add_test_areas():
    dataset_id = "test"
    dataset_geojson = geojson.loads(test_filepath.read_text())
    repo.insert_broadcast_area_library(
        dataset_id,
        name="Test areas",
        name_singular="test area",
        is_group=False,
    )

    areas_to_add = []
    for feature in dataset_geojson["features"]:
        f_id = feature["properties"]["id"]
        f_name = feature["properties"]["name"]

        print()  # noqa: T201
        print(f_name)  # noqa: T201

        feature, _, utm_crs = polygons_and_simplified_polygons(feature["geometry"])
        areas_to_add.append(
            [
                f"{dataset_id}-{f_id}",
                f_name,
                dataset_id,
                None,
                feature,
                feature,
                utm_crs,
                0,
            ]
        )

    repo.insert_broadcast_areas(areas_to_add, keep_old_polygons)


def add_additional_areas():
    dataset_id = "additional"
    dataset_geojson = geojson.loads(additional_filepath.read_text())
    repo.insert_broadcast_area_library(
        dataset_id,
        name="Additional areas",
        name_singular="additional area",
        is_group=False,
    )

    areas_to_add = []
    for feature in dataset_geojson["features"]:
        f_id = feature["properties"]["id"]
        f_name = feature["properties"]["name"]

        print()  # noqa: T201
        print(f_name)  # noqa: T201

        feature, _, utm_crs = polygons_and_simplified_polygons(feature["geometry"])
        areas_to_add.append(
            [
                f"{dataset_id}-{f_id}",
                f_name,
                dataset_id,
                None,
                feature,
                feature,
                utm_crs,
                0,
            ]
        )

    repo.insert_broadcast_areas(areas_to_add, keep_old_polygons)


def add_countries():
    dataset_id = "ctry19"
    dataset_geojson = geojson.loads(ctry19_filepath.read_text())
    repo.insert_broadcast_area_library(
        "ctry19",
        name="Countries",
        name_singular="country",
        is_group=False,
    )

    areas_to_add = []
    for feature in dataset_geojson["features"]:
        f_id = feature["properties"]["ctry19cd"]
        f_name = feature["properties"]["ctry19nm"]

        print()  # noqa: T201
        print(f_name)  # noqa: T201

        feature, simple_feature, utm_crs = polygons_and_simplified_polygons(feature["geometry"])
        areas_to_add.append(
            [
                f"ctry19-{f_id}",
                f_name,
                dataset_id,
                None,
                feature,
                simple_feature,
                utm_crs,
                estimate_number_of_smartphones_in_area(f_id),
            ]
        )

    repo.insert_broadcast_areas(areas_to_add, keep_old_polygons)


def add_police_force_areas():
    dataset_id = "pfa20"
    dataset_geojson = geojson.loads(pfa20_filepath.read_text())
    repo.insert_broadcast_area_library(
        dataset_id,
        name="Police forces in England and Wales",
        name_singular="police force",
        is_group=False,
    )

    areas_to_add = []

    london_geometry = {
        "type": "MultiPolygon",
        "coordinates": [],
    }

    for feature in dataset_geojson["features"]:
        f_id = feature["properties"]["PFA20CD"]
        f_name = feature["properties"]["PFA20NM"]

        if f_id in ("E23000001", "E23000034"):
            # Skip the Metropolitan Police and City of London for now
            # because we are going to combine them into one later
            london_geometry["coordinates"] += feature["geometry"]["coordinates"]
            continue

        print()  # noqa: T201
        print(f_name)  # noqa: T201

        feature, simple_feature, utm_crs = polygons_and_simplified_polygons(feature["geometry"])
        id = f"{dataset_id}-{f_id}"
        areas_to_add.append(
            [
                id,
                f_name,
                dataset_id,
                None,
                feature,
                simple_feature,
                utm_crs,
                POLICE_FORCE_AREAS[id],
            ]
        )

    # Manually add the Metropolitan Police and City of London as one combined area
    feature, simple_feature, utm_crs = polygons_and_simplified_polygons(london_geometry)

    areas_to_add.append(
        [
            "pfa20-LONDON",
            "London (Metropolitan & City of London)",
            dataset_id,
            None,
            feature,
            simple_feature,
            utm_crs,
            POLICE_FORCE_AREAS["pfa20-E23000001"] + POLICE_FORCE_AREAS["pfa20-E23000034"],
        ]
    )

    repo.insert_broadcast_areas(areas_to_add, keep_old_polygons)


def add_wards_local_authorities_and_counties():
    dataset_name = "Local authorities"
    dataset_name_singular = "local authority"
    dataset_id = "wd21-lad21-ctyua21"
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

    for feature in geojson.loads(wd21_filepath.read_text())["features"]:
        ward_code = feature["properties"]["WD21CD"]
        ward_name = feature["properties"]["WD21NM"]
        ward_id = "wd21-" + ward_code

        print()  # noqa: T201
        print(ward_name)  # noqa: T201

        la_id = "lad21-" + ward_code_to_la_id_mapping[ward_code]

        feature, simple_feature, utm_crs = polygons_and_simplified_polygons(feature["geometry"])

        if feature:
            rtree_index.insert(ward_id, Rect(*Polygons(feature).bounds))

        areas_to_add.append(
            [
                ward_id,
                ward_name,
                dataset_id,
                la_id,
                feature,
                simple_feature,
                utm_crs,
                estimate_number_of_smartphones_in_area(ward_code),
            ]
        )

    rtree_index_path.open("wb").write(pickle.dumps(rtree_index))
    repo.insert_broadcast_areas(areas_to_add, keep_old_polygons)


def _add_local_authorities(dataset_id):
    areas_to_add = []

    for feature in geojson.loads(lad21_filepath.read_text())["features"]:
        la_id = feature["properties"]["LAD21CD"]
        group_name = feature["properties"]["LAD21NM"]

        print()  # noqa: T201
        print(group_name)  # noqa: T201

        group_id = "lad21-" + la_id

        feature, simple_feature, utm_crs = polygons_and_simplified_polygons(feature["geometry"])

        ctyua_id = la_code_to_cty_id_mapping.get(la_id)
        areas_to_add.append(
            [
                group_id,
                group_name,
                dataset_id,
                "ctyua21-" + ctyua_id if ctyua_id else None,
                feature,
                simple_feature,
                utm_crs,
                None,
            ]
        )
    repo.insert_broadcast_areas(areas_to_add, keep_old_polygons)


# counties and unitary authorities
def _add_counties_and_unitary_authorities(dataset_id):
    areas_to_add = []
    for feature in geojson.loads(ctyua21_filepath.read_text())["features"]:
        ctyua_id = feature["properties"]["CTYUA21CD"]
        group_name = feature["properties"]["CTYUA21NM"]

        la_id = "lad21-" + ctyua_id
        if repo.get_areas([la_id]):
            continue

        group_id = "ctyua21-" + ctyua_id

        feature, simple_feature, utm_crs = polygons_and_simplified_polygons(feature["geometry"])

        areas_to_add.append(
            [
                group_id,
                group_name,
                dataset_id,
                None,
                feature,
                simple_feature,
                utm_crs,
                None,
            ]
        )

    repo.insert_broadcast_areas(areas_to_add, keep_old_polygons)


# cheeky global variable
keep_old_polygons = sys.argv[1:] == ["--keep-old-polygons"]
print("keep_old_polygons: ", keep_old_polygons)  # noqa: T201

repo = BroadcastAreasRepository()

if keep_old_polygons:
    repo.delete_library_data()
else:
    repo.delete_db()
    repo.create_tables()

add_test_areas()
add_additional_areas()
add_police_force_areas()
add_countries()
add_wards_local_authorities_and_counties()

most_detailed_polygons = formatted_list(
    sorted(point_counts, reverse=True)[:5],
    before_each="",
    after_each="",
)

print(  # noqa: T201
    "\n"
    "DONE\n"
    f"    Processed {len(point_counts):,} polygons.\n"
    f"    Cleaned up {len(invalid_polygons):,} polygons.\n"
    f"    Highest point counts once simplifed: {most_detailed_polygons}\n"
)
