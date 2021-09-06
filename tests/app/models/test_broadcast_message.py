import pytest

from app.models.broadcast_message import BroadcastMessage
from tests import broadcast_message_json


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
        [54],
    ]


def test_content_comes_from_attribute_not_template():
    broadcast_message = BroadcastMessage(broadcast_message_json())
    assert broadcast_message.content == 'This is a test'


def test_areas_raises_for_missing_areas():
    broadcast_message = BroadcastMessage(broadcast_message_json(
        area_ids=[
            'wd20-E05009372',
            'something else',
        ],
    ))

    with pytest.raises(RuntimeError) as exception:
        broadcast_message.areas

    assert str(exception.value) == (
        'BroadcastMessage has 2 areas but 1 found in the library'
    )
