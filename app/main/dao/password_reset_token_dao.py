from datetime import datetime, timedelta
from app import db
from app.models import PasswordResetToken


def insert(token):
    token.expiry_date = datetime.now() + timedelta(hours=1)
    db.session.add(token)
    db.session.commit()


def get_token(token):
    return PasswordResetToken.query.filter_by(token=token).first()
