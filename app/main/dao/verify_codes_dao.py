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


def get_code(user_id, code_type):
    verify_code = VerifyCodes.query.filter_by(user_id=user_id, code_type=code_type, code_used=False).first()
    return verify_code


def get_code_by_code(user_id, code_type):
    return VerifyCodes.query.filter_by(user_id=user_id, code_type=code_type).first()


def use_code(id):
    verify_code = VerifyCodes.query.get(id)
    verify_code.code_used = True
    db.session.add(verify_code)
    db.session.commit()


def add_code_with_expiry(user_id, code, code_type, expiry):
    code = VerifyCodes(user_id=user_id,
                       code=code,
                       code_type=code_type,
                       expiry_datetime=expiry)

    db.session.add(code)
    db.session.commit()
