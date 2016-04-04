from app.utils import email_safe


def test_email_safe_return_dot_separated_email_domain():
    test_name = 'SOME service  with+stuff+ b123'
    expected = 'some.service.withstuff.b123'
    actual = email_safe(test_name)
    assert actual == expected
