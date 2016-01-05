from app import db
from flask import current_app

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
DATE_FORMAT = "%Y-%m-%d"


class VerifyCodes(db.Model):
    __tablename__ = 'verify_codes'

    code_types = ['email', 'sms']

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True, unique=False, nullable=False)
    code = db.Column(db.String, nullable=False)
    code_type = db.Column(db.Enum(code_types, name='verify_code_types'), index=False, unique=False, nullable=False)
    expiry_datetime = db.Column(db.DateTime, nullable=False)
    code_used = db.Column(db.Boolean, default=False)


class Roles(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String, nullable=False, unique=True)


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, index=True, unique=False)
    email_address = db.Column(db.String(255), nullable=False, index=True, unique=True)
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
        if self.state != 'active':
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


user_to_service = db.Table(
    'user_to_service',
    db.Model.metadata,
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('service_id', db.Integer, db.ForeignKey('services.id'))
)


class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, index=False, unique=False, nullable=False)
    active = db.Column(db.Boolean, index=False, unique=False, nullable=False)
    limit = db.Column(db.BigInteger, index=False, unique=False, nullable=False)
    users = db.relationship('User', secondary=user_to_service, backref=db.backref('user_to_service', lazy='dynamic'))
    restricted = db.Column(db.Boolean, index=False, unique=False, nullable=False)

    def serialize(self):
        serialized = {
            'id': self.id,
            'name': self.name,
            'createdAt': self.created_at.strftime(DATETIME_FORMAT),
            'active': self.active,
            'restricted': self.restricted,
            'limit': self.limit,
            'user': self.users.serialize()
        }

        return filter_null_value_fields(serialized)


class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String, unique=True, index=True, nullable=False)
    user_id = db.Column(db.Integer,  db.ForeignKey('users.id'), unique=False, nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)


def filter_null_value_fields(obj):
    return dict(
        filter(lambda x: x[1] is not None, obj.items())
    )
