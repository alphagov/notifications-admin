from bs4 import BeautifulSoup
from flask_wtf import FlaskForm as Form

from app.main.forms import GovukRadiosField
from tests.conftest import normalize_spaces


def test_GovukRadiosField_supports_dividers(client_request):
    class FakeForm(Form):
        field = GovukRadiosField(
            choices=(
                ("1", "Aa"),
                ("2", "Bb"),
                GovukRadiosField.Divider("C to Y"),
                ("26", "Zz"),
            )
        )

    html = BeautifulSoup(FakeForm().field())

    assert [item["class"] for item in html.select(".govuk-radios>div")] == [
        ["govuk-radios__item"],
        ["govuk-radios__item"],
        ["govuk-radios__divider"],
        ["govuk-radios__item"],
    ]

    assert [
        (
            normalize_spaces(item.select_one("label").text),
            item.select_one("input")["value"],
        )
        for item in html.select(".govuk-radios__item")
    ] == [
        ("Aa", "1"),
        ("Bb", "2"),
        ("Zz", "26"),
    ]

    assert str(html.select_one(".govuk-radios__divider")) == '<div class="govuk-radios__divider">C to Y</div>'
