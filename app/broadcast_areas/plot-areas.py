#!/usr/bin/env python

import geojson
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import shapely.geometry as sgeom

from random import sample

from notifications_utils.safe_string import make_string_safe_for_id
from repo import BroadcastAreasRepository


def main():

    print()  # noqa: T001
    print("pick a library")  # noqa: T001
    for library in BroadcastAreasRepository().get_libraries():
        print("  ", library)  # noqa: T001

    library = input("> ")
    lid = make_string_safe_for_id(library)

    features = []
    simple_features = []

    inp = ""
    while True:
        print()  # noqa: T001
        print("pick an area, or press enter to skip")  # noqa: T001

        all_areas = BroadcastAreasRepository().get_all_areas_for_library(lid)
        some_areas = sample(all_areas, min(len(all_areas), 25))
        for area in some_areas:
            print("  ", area[0], area[1])  # noqa: T001

        inp = input("> ")
        if inp == "":
            break

        aid = inp.strip()
        area = BroadcastAreasRepository().get_areas([aid])[0]

        feature = area[-2]
        feature_shape = sgeom.shape(geojson.loads(feature)["geometry"])
        features.append(feature_shape)

        simple_feature = area[-1]
        simple_feature_shape = sgeom.shape(geojson.loads(simple_feature)["geometry"])
        simple_features.append(simple_feature_shape)

    print()  # noqa: T001
    print("Plotting")  # noqa: T001

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.set_extent([-20, 5, 40, 60], crs=ccrs.PlateCarree())

    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')

    ax.add_geometries(
        features,
        ccrs.PlateCarree(),
        facecolor='#00ff00',
        alpha=0.25,
    )

    ax.add_geometries(
        simple_features,
        ccrs.PlateCarree(),
        facecolor='#0000ff',
        alpha=0.25,
    )

    ax.scatter(
        [
            p[0]
            for f in simple_features
            for geom in (f.geoms if hasattr(f, 'geoms') else [f])
            for p in geom.exterior.coords
        ],
        [
            p[1]
            for f in simple_features
            for geom in (f.geoms if hasattr(f, 'geoms') else [f])
            for p in geom.exterior.coords
        ],
        transform=ccrs.PlateCarree(),
    )

    plt.show()


if __name__ == '__main__':
    main()
