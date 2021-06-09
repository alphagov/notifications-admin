import pytest
from notifications_utils.template import Template

from app.utils.templates import get_sample_template


@pytest.mark.parametrize("template_type", ["sms", "letter", "email"])
def test_get_sample_template_returns_template(template_type):
    template = get_sample_template(template_type)
    assert isinstance(template, Template)
