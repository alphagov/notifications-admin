from app.broadcast_areas.models import CustomBroadcastArea


def aggregate_areas(areas):
    areas = _convert_custom_areas_to_wards(areas)
    areas = _aggregate_wards_by_local_authority(areas)
    return areas


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
        area.parent if area.id.startswith('wd20-')
        else area for area in areas
    }
