from app.main import encryption


def test_encryption(notifications_admin):
    value = 's3curePassword!'

    encrypted = encryption.encrypt(value)

    assert encrypted == encryption.encrypt(value)
