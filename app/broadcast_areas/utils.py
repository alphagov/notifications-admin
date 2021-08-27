from collections import defaultdict

from app.broadcast_areas.models import CustomBroadcastArea


def aggregate_areas(areas):
    areas = _convert_custom_areas_to_wards(areas)
    areas = _aggregate_wards_by_local_authority(areas)
    areas = _aggregate_lower_tier_authorities(areas)
    return sorted(areas)


def _convert_custom_areas_to_wards(areas):
    results = set()

    for area in areas:
        if type(area) == CustomBroadcastArea:
            results |= set(area.overlapping_electoral_wards)
        else:
            results |= {area}

    return results


def _aggregate_wards_by_local_authority(areas):
    return {
        area.parent if area.is_electoral_ward
        else area for area in areas
    }


def _aggregate_lower_tier_authorities(areas):
    results = set()
    clusters = _cluster_lower_tier_authorities(areas)

    for cluster in clusters:
        # always show a single area cluster as itself (aggregation isn't helpful)
        if len(cluster) == 1:
            results |= set(cluster)
        # aggregate a single cluster with lots of areas (too complex to show in full)
        elif len(cluster) > 3:
            results |= {cluster[0].parent}
        # if cluster is 2 or 3 areas, and there are more than 1 cluster, aggregate the cluster
        elif len(clusters) > 1:
            area = cluster[0]
            results |= {area.parent or area}
        # else keep single 2-3 areas cluster in full (easy enough to understand)
        else:
            results |= set(cluster)

    return results


def _cluster_lower_tier_authorities(areas):
    result = defaultdict(lambda: [])

    for area in areas:
        # group lower tier authorities by "county"
        if area.is_lower_tier_local_authority:
            result[area.parent] += [area]
        # leave countries, unitary authorities as-is
        else:
            result[area] = [area]

    return result.values()
