from datetime import datetime, timedelta

from app import db
from app.main.encryption import hashpw
from app.models import VerifyCodes


def add_code(user_id, code, code_type):
    code = VerifyCodes(user_id=user_id,
                       code=hashpw(code),
                       code_type=code_type,
                       expiry_datetime=datetime.now() + timedelta(hours=1))

    db.session.add(code)
    db.session.commit()
    return code.id


def get_codes(user_id, code_type=None):
    if not code_type:
        return VerifyCodes.query.filter_by(user_id=user_id, code_used=False).all()
    return VerifyCodes.query.filter_by(user_id=user_id, code_type=code_type, code_used=False).all()


def get_code_by_code(user_id, code, code_type):
    return VerifyCodes.query.filter_by(user_id=user_id, code=code, code_type=code_type).first()


def use_code(id):
    verify_code = VerifyCodes.query.get(id)
    verify_code.code_used = True
    db.session.add(verify_code)
    db.session.commit()


def use_code_for_user_and_type(user_id, code_type):
    codes = VerifyCodes.query.filter_by(user_id=user_id, code_type=code_type, code_used=False).all()
    for verify_code in codes:
        verify_code.code_used = True
        db.session.add(verify_code)
    db.session.commit()


def get_code_by_id(id):
    return VerifyCodes.query.get(id)


def add_code_with_expiry(user_id, code, code_type, expiry):
    code = VerifyCodes(user_id=user_id,
                       code=hashpw(code),
                       code_type=code_type,
                       expiry_datetime=expiry)

    db.session.add(code)
    db.session.commit()
