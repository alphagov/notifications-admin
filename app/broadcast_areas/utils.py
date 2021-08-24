def aggregate_areas(areas):
    areas = _aggregate_wards_by_local_authority(areas)
    return areas


def _aggregate_wards_by_local_authority(areas):
    return {
        area.parent if area.id.startswith('wd20-')
        else area for area in areas
    }
