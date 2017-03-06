import pytest

from flask import Markup
from app import formatted_list


@pytest.mark.parametrize('items, kwargs, expected_output', [
    ([1], {}, '‘1’'),
    ([1, 2], {}, '‘1’ and ‘2’'),
    ([1, 2, 3], {}, '‘1’, ‘2’ and ‘3’'),
    ([1, 2, 3], {'prefix': 'foo', 'prefix_plural': 'bar'}, 'bar ‘1’, ‘2’ and ‘3’'),
    ([1], {'prefix': 'foo', 'prefix_plural': 'bar'}, 'foo ‘1’'),
    ([1, 2, 3], {'before_each': 'a', 'after_each': 'b'}, 'a1b, a2b and a3b'),
    ([1, 2, 3], {'conjunction': 'foo'}, '‘1’, ‘2’ foo ‘3’'),
    (['&'], {'before_each': '<i>', 'after_each': '</i>'}, '<i>&amp;</i>'),
    ([1, 2, 3], {'before_each': '<i>', 'after_each': '</i>'}, '<i>1</i>, <i>2</i> and <i>3</i>'),
])
def test_formatted_list(items, kwargs, expected_output):
    assert formatted_list(items, **kwargs) == expected_output


def test_formatted_list_returns_markup():
    assert isinstance(formatted_list([0]), Markup)
