import pytest

from app.models.broadcast_message import BroadcastMessage
from tests import broadcast_message_json
from tests.app.broadcast_areas.custom_polygons import (
    BRISTOL,
    BURFORD,
    CHELTENHAM_AND_GLOUCESTER,
    SANTA_A,
    SEVERN_ESTUARY,
    SKYE,
)


def test_simple_polygons(fake_uuid):
    broadcast_message = BroadcastMessage(broadcast_message_json(
        id_=fake_uuid,
        service_id=fake_uuid,
        template_id=fake_uuid,
        status='draft',
        created_by_id=fake_uuid,
        areas=[
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


def test_content_comes_from_attribute_not_template(fake_uuid):
    broadcast_message = BroadcastMessage(broadcast_message_json(
        id_=fake_uuid,
        service_id=fake_uuid,
        template_id=fake_uuid,
        status='draft',
        created_by_id=fake_uuid,
    ))
    assert broadcast_message.content == 'This is a test'


def test_raises_for_missing_areas(fake_uuid):
    broadcast_message = BroadcastMessage(broadcast_message_json(
        id_=fake_uuid,
        service_id=fake_uuid,
        template_id=fake_uuid,
        status='draft',
        created_by_id=fake_uuid,
        areas=[
            'wd20-E05009372',
            'something else',
        ],
    ))

    with pytest.raises(RuntimeError) as exception:
        broadcast_message.areas

    assert str(exception.value) == (
        'BroadcastMessage has 2 areas but 1 found in the library'
    )


@pytest.mark.parametrize('ward_ids, expected_parent_areas', (
    (
        [
            # Whitechapel
            'wd20-E05009336',
            # Hackney Central
            'wd20-E05009372',
            # Hackney Wick
            'wd20-E05009374',
        ], [
            'Hackney',
            'Tower Hamlets',
        ],
    ),
    (
        [
            # Hester’s Way, Cheltenham
            'wd20-E05004294',
            # Painswick & Upton, Stroud
            'wd20-E05010981',
        ], [
            'Cheltenham',
            'Stroud',
        ],
    ),
    (
        [
            # Hester’s Way, Cheltenham
            'wd20-E05004294',
            # Hackney Central
            'wd20-E05009372',
        ], [
            'Cheltenham',
            'Hackney',
        ],
    ),
    (
        [
            # Hester’s Way, Cheltenham
            'wd20-E05004294',
            # Painswick & Upton, Stroud
            'wd20-E05010981',
            # Hackney Central
            'wd20-E05009372',
        ], [
            'Gloucestershire',
            'Hackney',
        ],
    ),
    (
        [
            # High Peak, a lower tier local authority
            'lad20-E07000037',
        ],
        [
            'High Peak',
        ]
    ),
    (
        [
            # High Peak, a lower tier local authority
            'lad20-E07000037',
            # Derbyshire Dales, a lower tier local authority
            'lad20-E07000035',
        ],
        [
            'Derbyshire Dales',
            'High Peak',
        ]
    ),
    (
        [
            # High Peak, a lower tier local authority
            'lad20-E07000037',
            # Derbyshire Dales, a lower tier local authority
            'lad20-E07000035',
            # Staffordshire, an upper-tier local authority
            'ctyua19-E10000028',
        ],
        [
            'Derbyshire',
            'Staffordshire',
        ]
    ),
    (
        [
            # England
            'ctry19-E92000001',
        ],
        [
            'England',
        ]
    )
))
def test_immediate_parents(
    fake_uuid,
    ward_ids,
    expected_parent_areas,
):
    broadcast_message = BroadcastMessage(broadcast_message_json(
        id_=fake_uuid,
        service_id=fake_uuid,
        template_id=fake_uuid,
        status='draft',
        created_by_id=fake_uuid,
        areas=ward_ids,
    ))

    assert [
        area.name for area in broadcast_message.summarised_areas
    ] == expected_parent_areas


@pytest.mark.parametrize('simple_polygons, expected_parent_areas', (
    (
        [SKYE], [
            'Highland',
        ]
    ),
    (
        [BRISTOL], [
            'Bristol, City of',
        ]
    ),
    (
        [SEVERN_ESTUARY], [
            'Bristol, City of',
            # The polygon covers these lower-tier local authorities of
            # Gloucestershire which we group together to make things
            # cleaner
            # - Forest of Dean
            # - Gloucester
            # - Stroud
            # - Tewkesbury
            'Gloucestershire',
            'Monmouthshire',
            'Newport',
            'North Somerset',
            'South Gloucestershire',
        ]
    ),
    (
        [CHELTENHAM_AND_GLOUCESTER], [
            # These are all in lower-tier local authorities within
            # Gloucestershire, and we’re not targeting any other
            # upper-tier or unitary authorities so we display them
            # individually
            'Cheltenham',
            'Gloucester',
            'Stroud',
            'Tewkesbury',
        ]
    ),
    (
        [BURFORD], [
            # We’re only covering one lower-tier authority from each
            # upper tier authority, so we can be more specific by
            # listing them separately
            'Cotswold',
            'West Oxfordshire',
        ],
    ),
    (
        [CHELTENHAM_AND_GLOUCESTER, BURFORD], [
            # We group together the lower-tier areas from
            # Gloucestershire but still don’t say we’re targeting the
            # whole of Oxfordshire
            'Gloucestershire',
            'West Oxfordshire',
        ],
    ),
    (
        [SANTA_A], [
            # Does not overlap with the UK
        ],
    ),
))
def test_immediate_parents_for_custom_areas(
    fake_uuid,
    simple_polygons,
    expected_parent_areas,
):
    broadcast_message = BroadcastMessage(broadcast_message_json(
        id_=fake_uuid,
        service_id=fake_uuid,
        template_id=fake_uuid,
        status='draft',
        created_by_id=fake_uuid,
        areas=['Not relevant'],
        simple_polygons=simple_polygons,
    ))
    assert [
        area.name for area in broadcast_message.summarised_areas
    ] == expected_parent_areas
