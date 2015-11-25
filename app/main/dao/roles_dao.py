from app import db
from app.models import Roles


def insert_role(role):
    db.session.add(role)
    db.session.commit()


def get_role_by_id(id):
    return Roles.query.filter_by(id=id).first()
