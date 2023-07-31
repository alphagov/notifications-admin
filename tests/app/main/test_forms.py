import pytest

from app.main.forms import OrderableFieldsForm, StripWhitespaceStringField
from tests.conftest import set_config_values


class TestOrderableFieldsForm:
    def test_can_reorder_fields(self):
        class TestForm(OrderableFieldsForm):
            field1 = StripWhitespaceStringField()
            field2 = StripWhitespaceStringField()

            custom_field_order = ("field2", "field1")

        form = TestForm()
        assert [field.name for field in form] == ["field2", "field1"]

    def test_all_fields_must_be_listed(self):
        class TestForm(OrderableFieldsForm):
            field1 = StripWhitespaceStringField()
            field2 = StripWhitespaceStringField()
            field3 = StripWhitespaceStringField()

            custom_field_order = ("field2", "field1")

        with pytest.raises(RuntimeError) as e:
            TestForm()

        assert str(e.value) == (
            "When setting `OrderableFieldsForm.custom_field_order`, all fields must be listed exhaustively. "
            "The following fields are missing: {'field3'}."
        )

    def test_auto_injects_csrf_token_field(self, notify_admin, client_request):
        class TestForm(OrderableFieldsForm):
            field1 = StripWhitespaceStringField()
            field2 = StripWhitespaceStringField()

            custom_field_order = ("field2", "field1")

        with set_config_values(notify_admin, dict(WTF_CSRF_ENABLED=True)):
            form = TestForm()
            assert [field.name for field in form] == ["csrf_token", "field2", "field1"]
