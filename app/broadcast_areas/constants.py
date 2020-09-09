import math

SMARTPHONE_OWNERSHIP_BY_AGE_RANGE = {
    # If no children have a phone when they’re born but 100% of
    # children have a phone by age 16 then 50% is a rough
    # approximation of how many children have phones
    (0, 15): 0.50,
    # https://www.finder.com/uk/mobile-internet-statistics
    (16, 24): 1.00,
    (25, 34): 0.97,
    (35, 44): 0.91,
    (45, 54): 0.88,
    (55, 64): 0.73,
    (65, math.inf): 0.40,
}

MEDIAN_AGE_UK = 40

for min, max in SMARTPHONE_OWNERSHIP_BY_AGE_RANGE.keys():
    if min <= MEDIAN_AGE_UK <= max:
        MEDIAN_AGE_RANGE_UK = (min, max)


class CITY_OF_LONDON:
    WARDS = (
        'E05009289', 'E05009290', 'E05009291', 'E05009292', 'E05009293',
        'E05009294', 'E05009295', 'E05009296', 'E05009297', 'E05009298',
        'E05009299', 'E05009300', 'E05009301', 'E05009302', 'E05009303',
        'E05009304', 'E05009305', 'E05009306', 'E05009307', 'E05009308',
        'E05009309', 'E05009310', 'E05009311', 'E05009312',
    )
    # https://data.london.gov.uk/blog/daytime-population-of-london-2014/
    DAYTIME_POPULATION = 553_000
    # Approx area of the polygons we’re storing, not the actual area
    AREA_SQUARE_MILES = 1.78


class BRYHER:
    WD20_CODE = 'E05011090'
    POPULATION = 84
