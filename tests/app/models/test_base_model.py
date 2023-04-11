import pytest

from app.models import JSONModel


def test_looks_up_from_dict():
    class Custom(JSONModel):
        ALLOWED_PROPERTIES = {"foo"}
        __sort_attribute__ = "foo"

    assert Custom({"foo": "bar"}).foo == "bar"


def test_raises_when_overriding_custom_properties():
    class Custom(JSONModel):

        ALLOWED_PROPERTIES = {"foo"}
        __sort_attribute__ = "foo"

        @property
        def foo(self):
            pass

    with pytest.raises(AttributeError) as e:
        Custom({"foo": "NOPE"})

    assert str(e.value) == "can't set attribute"


@pytest.mark.parametrize(
    "json_response",
    (
        {},
        {"foo": "bar"},  # Should still raise an exception
    ),
)
def test_model_raises_for_unknown_attributes(json_response):
    class Custom(JSONModel):
        ALLOWED_PROPERTIES = set()
        __sort_attribute__ = None

    model = Custom(json_response)
    assert model.ALLOWED_PROPERTIES == set()

    with pytest.raises(AttributeError) as e:
        model.foo  # noqa: B018

    assert str(e.value) == "'Custom' object has no attribute 'foo'"


def test_model_raises_keyerror_if_item_missing_from_dict():
    class Custom(JSONModel):
        ALLOWED_PROPERTIES = {"foo"}
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
        ALLOWED_PROPERTIES = set()
        __sort_attribute__ = None

        @property
        def foo(self):
            raise AttributeError("Something has gone wrong")

    with pytest.raises(AttributeError) as e:
        Custom(json_response).foo  # noqa: B018

    assert str(e.value) == "Something has gone wrong"


def test_dynamic_properties_are_introspectable():
    class Custom(JSONModel):
        ALLOWED_PROPERTIES = {"foo", "bar", "baz"}
        __sort_attribute__ = "foo"

    model = Custom({"foo": None, "bar": None, "baz": None})

    assert dir(model)[-3:] == ["bar", "baz", "foo"]
