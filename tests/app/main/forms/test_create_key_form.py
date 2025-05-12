import pytest
from werkzeug.datastructures import MultiDict

from app.main.forms import CreateKeyForm
from app.models.api_key import APIKeys


@pytest.mark.parametrize(
    "expiry_date, expected_errors",
    (
        (None, ["A key with this name already exists"]),
        ("2001-01-01 01:01:01", None),
    ),
)
def test_return_validation_error_when_key_name_exists(
    client_request,
    expiry_date,
    expected_errors,
    mocker,
):
    mocker.patch(
        "app.models.api_key.api_key_api_client.get_api_keys",
        return_value={
            "apiKeys": [
                {
                    "name": "some key",
                    "expiry_date": expiry_date,
                },
                {
                    "name": "another key",
                    "expiry_date": None,
                },
            ]
        },
    )

    form = CreateKeyForm(APIKeys("foo"), formdata=MultiDict([("key_name", "Some key")]))

    form.key_type.choices = [("a", "a"), ("b", "b")]
    form.validate()
    assert form.errors.get("key_name") == expected_errors


@pytest.mark.parametrize(
    "key_type, expected_error", [("", "Select a type of API key"), ("invalid", "Select a type of API key")]
)
def test_return_validation_error_when_key_type_not_chosen(client_request, key_type, expected_error):
    form = CreateKeyForm([], formdata=MultiDict([("key_name", "Some key"), ("key_type", key_type)]))
    form.key_type.choices = [("a", "a"), ("b", "b")]
    form.validate()
    assert form.errors["key_type"] == [expected_error]
