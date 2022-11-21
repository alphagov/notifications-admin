from unittest.mock import PropertyMock


class ComparablePropertyMock(PropertyMock):
    """A minimal extension of PropertyMock that allows it to be compared against another value"""

    def __lt__(self, other):
        return self() < other
