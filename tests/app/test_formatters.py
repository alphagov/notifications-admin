from app.formatters import sentence_case


def test_sentence_case():
    assert sentence_case("domain 1 cannot contain @") == "Domain 1 cannot contain @"
    assert (
        sentence_case("mobile number 2 does not look like a UK mobile number")
        == "Mobile number 2 does not look like a UK mobile number"
    )
