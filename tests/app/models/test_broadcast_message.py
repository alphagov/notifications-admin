import pytest

from app.broadcast_areas.models import CustomBroadcastAreas
from app.models.broadcast_message import BroadcastMessage
from tests import broadcast_message_json


@pytest.mark.parametrize('areas, expected_area_ids', [
    ({'simple_polygons': []}, []),
    ({'ids': ['123'], 'simple_polygons': []}, ['123'])
])
def test_area_ids(
    areas,
    expected_area_ids,
):
    broadcast_message = BroadcastMessage(broadcast_message_json(
        areas=areas
    ))

    assert broadcast_message.area_ids == expected_area_ids


def test_simple_polygons():
    broadcast_message = BroadcastMessage(broadcast_message_json(
        area_ids=[
            # Hackney Central
            'wd20-E05009372',
            # Hackney Wick
            'wd20-E05009374',
        ],
    ))

    assert [
        [
            len(polygon)
            for polygon in broadcast_message.polygons.as_coordinate_pairs_lat_long
        ],
        [
            len(polygon)
            for polygon in broadcast_message.simple_polygons.as_coordinate_pairs_lat_long
        ],
    ] == [
        # One polygon for each area
        [27, 31],
        # Because the areas are close to each other, the simplification
        # and unioning process results in a single polygon with fewer
        # total coordinates
        [55],
    ]


def test_content_comes_from_attribute_not_template():
    broadcast_message = BroadcastMessage(broadcast_message_json())
    assert broadcast_message.content == 'This is a test'


@pytest.mark.parametrize(('areas', 'expected_length'), [
    ({'ids': []}, 0),
    ({'ids': ['wd20-E05009372']}, 1),
    ({'no data': 'just created'}, 0),
    ({'names': ['somewhere'], 'simple_polygons': [[[3.5, 1.5]]]}, 1)
])
def test_areas(
    areas,
    expected_length
):
    broadcast_message = BroadcastMessage(broadcast_message_json(
        areas=areas
    ))

    assert len(list(broadcast_message.areas)) == expected_length


def test_areas_treats_missing_ids_as_custom_broadcast(notify_admin):
    broadcast_message = BroadcastMessage(broadcast_message_json(
        areas={
            'ids': [
                'wd20-E05009372',
                'something else',
            ],
            # although the IDs may no longer be usable, we can
            # expect the broadcast to have names and polygons,
            # which is enough to show the user something
            'names': [
                'wd20 name',
                'something else name'
            ],
            'simple_polygons': [[[1, 2]]]
        }
    ))

    assert len(list(broadcast_message.areas)) == 2
    assert type(broadcast_message.areas) == CustomBroadcastAreas
