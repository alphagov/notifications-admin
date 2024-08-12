from app.formatters import message_count_label, sentence_case


def test_sentence_case():
    assert sentence_case("domain 1 cannot contain @") == "Domain 1 cannot contain @"
    assert (
        sentence_case("mobile number 2 does not look like a UK mobile number")
        == "Mobile number 2 does not look like a UK mobile number"
    )


def test_message_count_label_for_unsubscribe_requests():
    assert message_count_label(count=1, message_type="unsubscribe request", suffix="") == "unsubscribe request"
    assert message_count_label(count=2, message_type="unsubscribe request", suffix="") == "unsubscribe requests"
    assert message_count_label(count=1, message_type="request", suffix="") == "request"
    assert message_count_label(count=2, message_type="request", suffix="") == "requests"
