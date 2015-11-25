from app import db
from app.models import Users


def insert_user(user):
    db.session.add(user)
    db.session.commit()


def get_user_by_id(id):
    return Users.query.filter_by(id=id).first()
