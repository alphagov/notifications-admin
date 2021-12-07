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
        'E05009288', 'E05009289', 'E05009290', 'E05009291', 'E05009292',
        'E05009293', 'E05009294', 'E05009295', 'E05009296', 'E05009297',
        'E05009298', 'E05009299', 'E05009300', 'E05009301', 'E05009302',
        'E05009303', 'E05009304', 'E05009305', 'E05009306', 'E05009307',
        'E05009308', 'E05009309', 'E05009310', 'E05009311', 'E05009312',
    )
    # https://data.london.gov.uk/blog/daytime-population-of-london-2014/
    DAYTIME_POPULATION = 553_000
    # Exact area of the polygons we’re storing, which matches the 2.9km²
    # given by https://en.wikipedia.org/wiki/City_of_London
    AREA_SQUARE_METRES = 2_885_598


class BRYHER:
    WD20_CODE = 'E05011090'
    POPULATION = 84


def estimate_number_of_smartphones_for_population(population):
    smartphone_ownership_for_area_by_age_range = {}

    for range, ownership in SMARTPHONE_OWNERSHIP_BY_AGE_RANGE.items():
        min, max = range
        smartphone_ownership_for_area_by_age_range[range] = sum(
            people
            for age, people in population
            if min <= age <= max
        ) * ownership

    total_population = sum(dict(population).values())
    total_phones = sum(smartphone_ownership_for_area_by_age_range.values())

    print(  # noqa: T001
        f'    Population:{total_population: 11,.0f}'
        f'    Phones:{total_phones: 11,.0f}'
    )

    return total_phones
