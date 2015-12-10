from datetime import datetime

from app.main.dao import users_dao
from app.models import User


def create_test_user():
    user = User(name='Test User',
                password='somepassword',
                email_address='test@user.gov.uk',
                mobile_number='+441234123412',
                created_at=datetime.now(),
                role_id=1,
                state='pending')
    users_dao.insert_user(user)
    return user
