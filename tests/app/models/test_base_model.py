import pytest

from app.models import JSONModel


def test_looks_up_from_dict():

    class Custom(JSONModel):
        ALLOWED_PROPERTIES = {'foo'}

    assert Custom({'foo': 'bar'}).foo == 'bar'


def test_prefers_property_to_dict():

    class Custom(JSONModel):

        ALLOWED_PROPERTIES = {'foo'}

        @property
        def foo(self):
            return 'bar'

    assert Custom({'foo': 'NOPE'}).foo == 'bar'


@pytest.mark.parametrize('json_response', (
    {},
    {'foo': 'bar'},  # Should still raise an exception
))
def test_model_raises_for_unknown_attributes(json_response):

    model = JSONModel(json_response)
    assert model.ALLOWED_PROPERTIES == set()

    with pytest.raises(AttributeError) as e:
        model.foo

    assert str(e.value) == (
        "'JSONModel' object has no attribute 'foo' and 'foo' is not a "
        "field in the underlying JSON"
    )


def test_model_raises_keyerror_if_item_missing_from_dict():

    class Custom(JSONModel):
        ALLOWED_PROPERTIES = {'foo'}

    with pytest.raises(KeyError) as e:
        Custom({}).foo

    assert str(e.value) == "'foo'"


@pytest.mark.parametrize('json_response', (
    {},
    {'foo': 'bar'},  # Should be ignored
))
def test_model_doesnt_swallow_attribute_errors(json_response):

    class Custom(JSONModel):
        @property
        def foo(self):
            raise AttributeError('Something has gone wrong')

    with pytest.raises(AttributeError) as e:
        Custom(json_response).foo

    assert str(e.value) == 'Something has gone wrong'
