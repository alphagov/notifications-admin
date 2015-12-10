from app.main.encryption import hashpw, check_hash


def test_should_hash_password():
    password = 'passwordToHash'
    assert password != hashpw(password)


def test_should_check_password():
    value = 's3curePassword!'
    encrypted = hashpw(value)
    assert check_hash(value, encrypted) is True


def test_checkpw_should_fail_when_pw_does_not_match():
    value = hashpw('somePassword')
    assert check_hash('somethingDifferent', value) is False
