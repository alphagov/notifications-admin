import pytest

from app.broadcast_areas.models import CustomBroadcastArea
from tests.app.broadcast_areas.custom_polygons import BRISTOL, SANTA_A, SKYE


@pytest.mark.parametrize(('simple_polygon', 'expected_wards_length'), [
    (SKYE, 1),
    (BRISTOL, 12),
    (SANTA_A, 0)  # does not overlap with UK
])
def test_custom_broadcast_area_overlapping_electoral_wards(
    simple_polygon,
    expected_wards_length,
):
    custom_area = CustomBroadcastArea(
        name='foo', polygons=[simple_polygon]
    )

    assert len(custom_area.overlapping_electoral_wards) == expected_wards_length
