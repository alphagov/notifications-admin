import pytest

from app.models import JSONModel


def test_looks_up_from_dict():
    class Custom(JSONModel):
        foo: str
        __sort_attribute__ = "foo"

    assert Custom({"foo": "bar"}).foo == "bar"


def test_raises_when_overriding_custom_properties():
    class Custom(JSONModel):
        foo: str
        __sort_attribute__ = "foo"

        @property
        def foo(self):
            pass

    with pytest.raises(AttributeError) as e:
        Custom({"foo": "NOPE"})

    assert str(e.value) == (
        "property 'foo' of 'test_raises_when_overriding_custom_properties.<locals>.Custom' object has no setter"
    )


@pytest.mark.parametrize(
    "json_response",
    (
        {},
        {"foo": "bar"},  # Should still raise an exception
    ),
)
def test_model_raises_for_unknown_attributes(json_response):
    class Custom(JSONModel):
        __sort_attribute__ = None

    model = Custom(json_response)

    with pytest.raises(AttributeError) as e:
        model.foo  # noqa: B018

    assert str(e.value) == "'Custom' object has no attribute 'foo'"


def test_model_raises_keyerror_if_item_missing_from_dict():
    class Custom(JSONModel):
        foo: str
        __sort_attribute__ = "foo"

    with pytest.raises(AttributeError) as e:
        Custom({}).foo  # noqa: B018

    assert str(e.value) == "'Custom' object has no attribute 'foo'"


@pytest.mark.parametrize(
    "json_response",
    (
        {},
        {"foo": "bar"},  # Should be ignored
    ),
)
def test_model_doesnt_swallow_attribute_errors(json_response):
    class Custom(JSONModel):
        __sort_attribute__ = None

        @property
        def foo(self):
            raise AttributeError("Something has gone wrong")

    with pytest.raises(AttributeError) as e:
        Custom(json_response).foo  # noqa: B018

    assert str(e.value) == "Something has gone wrong"


def test_dynamic_properties_are_introspectable():
    class Custom(JSONModel):
        foo: str
        bar: str
        baz: str
        __sort_attribute__ = "foo"

    model = Custom({"foo": None, "bar": None, "baz": None})

    for property_name in ["bar", "baz", "foo"]:
        assert property_name in dir(model)

    assert model.foo is None
    assert model.bar is None
    assert model.baz is None


def test_attribute_inheritence():
    class Parent1(JSONModel):
        foo: str

    class Parent2(JSONModel):
        bar: str

    class Child(Parent1, Parent2):
        __sort_attribute__ = "foo"
        baz: str

    instance = Child({"foo": 1, "bar": 2, "baz": 3})

    assert instance.foo == "1"
    assert instance.bar == "2"
    assert instance.baz == "3"
