from datetime import datetime

from app.main.dao import users_dao
from app.models import Users


def test_get_all_users_returns_all_users(notifications_admin, notifications_admin_db):
    user1 = Users(name='test one',
                  password='somepassword',
                  email_address='test1@get_all.gov.uk',
                  mobile_number='+441234123412',
                  created_at=datetime.now(),
                  role_id=1)
    user2 = Users(name='test two',
                  password='some2ndpassword',
                  email_address='test2@get_all.gov.uk',
                  mobile_number='+441234123412',
                  created_at=datetime.now(),
                  role_id=1)
    user3 = Users(name='test three',
                  password='some2ndpassword',
                  email_address='test2@get_all.gov.uk',
                  mobile_number='+441234123412',
                  created_at=datetime.now(),
                  role_id=1)

    users_dao.insert_user(user1)
    users_dao.insert_user(user2)
    users_dao.insert_user(user3)
    users = users_dao.get_all_users()
    assert len(users) == 3
    assert users == [user1, user2, user3]
