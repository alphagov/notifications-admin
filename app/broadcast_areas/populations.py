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


POLICE_FORCE_AREAS = {
    # Estimated by calculating the overlap with electoral wards
    'pfa20-E23000001': 5499865,  # Metropolitan Police
    'pfa20-E23000002': 347193,   # Cumbria
    'pfa20-E23000003': 931068,   # Lancashire
    'pfa20-E23000004': 1035309,  # Merseyside
    'pfa20-E23000005': 1900035,  # Greater Manchester
    'pfa20-E23000006': 667818,   # Cheshire
    'pfa20-E23000007': 1055281,  # Northumbria
    'pfa20-E23000008': 458019,   # Durham
    'pfa20-E23000009': 591255,   # North Yorkshire
    'pfa20-E23000010': 1712333,  # West Yorkshire
    'pfa20-E23000011': 843372,   # South Yorkshire
    'pfa20-E23000012': 660480,   # Humberside
    'pfa20-E23000013': 340795,   # Cleveland
    'pfa20-E23000014': 2156825,  # West Midlands
    'pfa20-E23000015': 819624,   # Staffordshire
    'pfa20-E23000016': 917312,   # West Mercia
    'pfa20-E23000017': 420089,   # Warwickshire
    'pfa20-E23000018': 764621,   # Derbyshire
    'pfa20-E23000019': 854309,   # Nottinghamshire
    'pfa20-E23000020': 469432,   # Lincolnshire
    'pfa20-E23000021': 807566,   # Leicestershire
    'pfa20-E23000022': 545165,   # Northamptonshire
    'pfa20-E23000023': 361479,   # Cambridgeshire
    'pfa20-E23000024': 634492,   # Norfolk
    'pfa20-E23000025': 529853,   # Suffolk
    'pfa20-E23000026': 492654,   # Bedfordshire
    'pfa20-E23000027': 825700,   # Hertfordshire
    'pfa20-E23000028': 1842426,  # Essex
    'pfa20-E23000029': 1255799,  # Thames Valley
    'pfa20-E23000030': 1287584,  # Hampshire
    'pfa20-E23000031': 863499,   # Surrey
    'pfa20-E23000032': 1322246,  # Kent
    'pfa20-E23000033': 868383,   # Sussex
    'pfa20-E23000034': 528943,   # London, City of
    'pfa20-E23000035': 1360980,  # Devon & Cornwall
    'pfa20-E23000036': 1245304,  # Avon and Somerset
    'pfa20-E23000037': 405117,   # Gloucestershire
    'pfa20-E23000038': 516349,   # Wiltshire
    'pfa20-E23000039': 530412,   # Dorset
    'pfa20-W15000001': 486462,   # North Wales
    'pfa20-W15000002': 426139,   # Gwent
    'pfa20-W15000003': 978408,   # South Wales
    'pfa20-W15000004': 357392,   # Dyfed-Powys
}


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

    print(  # noqa: T201
        f'    Population:{total_population: 11,.0f}'
        f'    Phones:{total_phones: 11,.0f}'
    )

    return total_phones
