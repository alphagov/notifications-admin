import pytest
from freezegun import freeze_time

from app import format_datetime_relative
from app.formatters import email_safe, round_to_significant_figures
from app.utils import get_logo_cdn_domain, merge_jsonlike


@pytest.mark.parametrize('service_name, safe_email', [
    ('name with spaces', 'name.with.spaces'),
    ('singleword', 'singleword'),
    ('UPPER CASE', 'upper.case'),
    ('Service - with dash', 'service.with.dash'),
    ('lots      of spaces', 'lots.of.spaces'),
    ('name.with.dots', 'name.with.dots'),
    ('name-with-other-delimiters', 'namewithotherdelimiters'),
    ('.leading', 'leading'),
    ('trailing.', 'trailing'),
    ('üńïçödë wördś', 'unicode.words'),
])
def test_email_safe_return_dot_separated_email_domain(service_name, safe_email):
    assert email_safe(service_name) == safe_email


def test_get_cdn_domain_on_localhost(client, mocker):
    mocker.patch.dict('app.current_app.config', values={'ADMIN_BASE_URL': 'http://localhost:6012'})
    domain = get_logo_cdn_domain()
    assert domain == 'static-logos.notify.tools'


def test_get_cdn_domain_on_non_localhost(client, mocker):
    mocker.patch.dict('app.current_app.config', values={'ADMIN_BASE_URL': 'https://some.admintest.com'})
    domain = get_logo_cdn_domain()
    assert domain == 'static-logos.admintest.com'


@pytest.mark.parametrize('time, human_readable_datetime', [
    ('2018-03-14 09:00', '14 March at 9:00am'),
    ('2018-03-14 15:00', '14 March at 3:00pm'),

    ('2018-03-15 09:00', '15 March at 9:00am'),
    ('2018-03-15 15:00', '15 March at 3:00pm'),

    ('2018-03-19 09:00', '19 March at 9:00am'),
    ('2018-03-19 15:00', '19 March at 3:00pm'),
    ('2018-03-19 23:59', '19 March at 11:59pm'),

    ('2018-03-20 00:00', '19 March at midnight'),  # we specifically refer to 00:00 as belonging to the day before.
    ('2018-03-20 00:01', 'yesterday at 12:01am'),
    ('2018-03-20 09:00', 'yesterday at 9:00am'),
    ('2018-03-20 15:00', 'yesterday at 3:00pm'),
    ('2018-03-20 23:59', 'yesterday at 11:59pm'),

    ('2018-03-21 00:00', 'yesterday at midnight'),  # we specifically refer to 00:00 as belonging to the day before.
    ('2018-03-21 00:01', 'today at 12:01am'),
    ('2018-03-21 09:00', 'today at 9:00am'),
    ('2018-03-21 12:00', 'today at midday'),
    ('2018-03-21 15:00', 'today at 3:00pm'),
    ('2018-03-21 23:59', 'today at 11:59pm'),

    ('2018-03-22 00:00', 'today at midnight'),  # we specifically refer to 00:00 as belonging to the day before.
    ('2018-03-22 00:01', 'tomorrow at 12:01am'),
    ('2018-03-22 09:00', 'tomorrow at 9:00am'),
    ('2018-03-22 15:00', 'tomorrow at 3:00pm'),
    ('2018-03-22 23:59', 'tomorrow at 11:59pm'),

    ('2018-03-23 00:01', '23 March at 12:01am'),
    ('2018-03-23 09:00', '23 March at 9:00am'),
    ('2018-03-23 15:00', '23 March at 3:00pm'),

])
def test_format_datetime_relative(time, human_readable_datetime):
    with freeze_time('2018-03-21 12:00'):
        assert format_datetime_relative(time) == human_readable_datetime


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


@pytest.mark.parametrize('value, significant_figures, expected_result', (
    (0, 1, 0),
    (0, 2, 0),
    (12_345, 1, 10_000),
    (12_345, 2, 12_000),
    (12_345, 3, 12_300),
    (12_345, 9, 12_345),
    (12_345.6789, 1, 10_000),
    (12_345.6789, 9, 12_345),
    (-12_345, 1, -10_000),
))
def test_round_to_significant_figures(value, significant_figures, expected_result):
    assert round_to_significant_figures(value, significant_figures) == expected_result
