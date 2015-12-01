from flask.ext.bcrypt import generate_password_hash, check_password_hash


def hashpw(password):
    return generate_password_hash(password.encode('UTF-8'), 10)


def checkpw(password, hashed_password):
    # If salt is invalid throws a 500 should add try/catch here
    return check_password_hash(hashed_password, password)
