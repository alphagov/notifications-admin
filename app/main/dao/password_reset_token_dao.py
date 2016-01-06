from datetime import datetime, timedelta
from app import db
from app.models import PasswordResetToken


def insert(token, user_id):
    password_reset_token = PasswordResetToken(token=token,
                                              user_id=user_id,
                                              expiry_date=datetime.now() + timedelta(hours=1))
    insert_token(password_reset_token)


def insert_token(password_reset_token):
    db.session.add(password_reset_token)
    db.session.commit()


def get_token(token):
    return PasswordResetToken.query.filter_by(token=token).first()
