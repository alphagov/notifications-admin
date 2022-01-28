import pytest

from app.utils import merge_jsonlike


@pytest.mark.parametrize("source_object, destination_object, expected_result", [
    # simple dicts:
    ({"a": "b"}, {"c": "d"}, {"a": "b", "c": "d"}),
    # dicts with nested dict, both under same key, additive behaviour:
    ({"a": {"b": "c"}}, {"a": {"e": "f"}}, {"a": {"b": "c", "e": "f"}}),
    # same key in both dicts, value is a string, destination supercedes source:
    ({"a": "b"}, {"a": "c"}, {"a": "c"}),
    # nested dict added to new key of dict, additive behaviour:
    ({"a": "b"}, {"c": {"d": "e"}}, {"a": "b", "c": {"d": "e"}}),
    # lists with same length but different items, destination supercedes source:
    (["b", "c", "d"], ["b", "e", "f"], ["b", "e", "f"]),
    # lists in dicts behave as top level lists
    ({"a": ["b", "c", "d"]}, {"a": ["b", "e", "f"]}, {"a": ["b", "e", "f"]}),
    # lists with same string in both, at different positions, result in duplicates keeping their positions
    (["a", "b", "c", "d"], ["d", "e", "f"], ["d", "e", "f", "d"]),
    # lists with same dict in both result in a list with one instance of that dict
    ([{"b": "c"}], [{"b": "c"}], [{"b": "c"}]),
    # if dicts in lists have different values, they are not merged
    ([{"b": "c"}], [{"b": "e"}], [{"b": "e"}]),
    # if nested dicts in lists have different keys, additive behaviour
    ([{"b": "c"}], [{"d": {"e": "f"}}], [{"b": "c", "d": {"e": "f"}}]),
    # if dicts in destination list but not source, they just get added to end of source
    ([{"a": "b"}], [{"a": "b"}, {"a": "b"}, {"c": "d"}], [{"a": "b"}, {"a": "b"}, {"c": "d"}]),
    # merge a dict with a null object returns that dict (does not work the other way round)
    ({"a": {"b": "c"}}, None, {"a": {"b": "c"}}),
    # double nested dicts, new adds new Boolean key: value, additive behaviour
    ({"a": {"b": {"c": "d"}}}, {"a": {"b": {"e": True}}}, {"a": {"b": {"c": "d", "e": True}}}),
    # double nested dicts, both have same key, different values, destination supercedes source
    ({"a": {"b": {"c": "d"}}}, {"a": {"b": {"c": "e"}}}, {"a": {"b": {"c": "e"}}})
])
def test_merge_jsonlike_merges_jsonlike_objects_correctly(source_object, destination_object, expected_result):
    merge_jsonlike(source_object, destination_object)
    assert source_object == expected_result
