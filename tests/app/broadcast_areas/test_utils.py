import pytest

from app.broadcast_areas.utils import aggregate_areas
from app.models.broadcast_message import BroadcastMessage
from tests import broadcast_message_json
from tests.app.broadcast_areas.custom_polygons import (
    BRISTOL,
    BURFORD,
    CHELTENHAM,
    SANTA_A,
    SKYE,
)


@pytest.mark.parametrize(('area_ids', 'expected_area_names'), [
    (
        [
            'wd20-E05004294',  # Hester’s Way, Cheltenham (electoral ward)
            'wd20-E05010981',  # Painswick & Upton, Stroud (electoral ward)
        ], [
            'Cheltenham',  # in Gloucestershire (upper tier authority)
            'Stroud',  # in Gloucestershire
        ],
    ),
    (
        [
            'wd20-E05004294',  # Hester’s Way, Cheltenham (electoral ward)
            'wd20-E05009372',  # Hackney Central (electoral ward)
        ], [
            'Cheltenham',  # in Gloucestershire (upper tier authority)
            'Hackney',  # in Greater London* (DB doesn't know this)
        ],
    ),
    (
        [
            'lad20-E07000037',  # High Peak (lower tier authority)
        ],
        [
            'High Peak',  # in Derbyshire (upper tier authority)
        ]
    ),
    (
        [
            'lad20-E07000037',  # High Peak (lower tier authority)
            'lad20-E07000035',  # Derbyshire Dales (lower tier authority)
        ],
        [
            'Derbyshire Dales',  # in Derbyshire (upper tier authority)
            'High Peak',  # in Derbyshire
        ]
    ),
    (
        [
            'ctry19-E92000001',  # England
        ],
        [
            'England',
        ]
    )
])
def test_aggregate_areas(
    area_ids,
    expected_area_names,
):
    broadcast_message = BroadcastMessage(
        broadcast_message_json(area_ids=area_ids)
    )

    assert sorted(
        area.name for area in aggregate_areas(broadcast_message.areas)
    ) == expected_area_names
