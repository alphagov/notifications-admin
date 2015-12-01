from app import db
from flask import current_app

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
DATE_FORMAT = "%Y-%m-%d"


class Roles(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String, nullable=False, unique=True)


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, index=True, unique=True)
    email_address = db.Column(db.String(255), nullable=False, index=True)
    password = db.Column(db.String, index=False, unique=False, nullable=False)
    mobile_number = db.Column(db.String, index=False, unique=False, nullable=False)
    created_at = db.Column(db.DateTime, index=False, unique=False, nullable=False)
    updated_at = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    password_changed_at = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), index=True, unique=False, nullable=False)
    logged_in_at = db.Column(db.DateTime, nullable=True)
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)
    state = db.Column(db.String, nullable=False, default='pending')

    def serialize(self):
        serialized = {
            'id': self.id,
            'name': self.name,
            'emailAddress': self.email_address,
            'locked': self.failed_login_count > current_app.config['MAX_FAILED_LOGIN_COUNT'],
            'createdAt': self.created_at.strftime(DATETIME_FORMAT),
            'updatedAt': self.updated_at.strftime(DATETIME_FORMAT),
            'role': self.role,
            'passwordChangedAt': self.password_changed_at.strftime(DATETIME_FORMAT),
            'failedLoginCount': self.failed_login_count
        }

        return filter_null_value_fields(serialized)

    def is_authenticated(self):
        return True

    def is_active(self):
        if self.state == 'inactive':
            return False
        else:
            return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def is_locked(self):
            if self.failed_login_count < current_app.config['MAX_FAILED_LOGIN_COUNT']:
                return False
            else:
                return True


def filter_null_value_fields(obj):
    return dict(
        filter(lambda x: x[1] is not None, obj.items())
    )
