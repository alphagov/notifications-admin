from datetime import datetime

from app import db
from app.models import Service


def insert_new_service(service_name, user):
    service = Service(name=service_name,
                      created_at=datetime.now(),
                      limit=1000,
                      active=False,
                      restricted=True)
    try:
        add_service(service)
        service.users.append(user)
        db.session.commit()
        return service.id
    except Exception as e:
        print(e)
        raise e


def get_service_by_id(id):
    return Service.query.get(id)


def unrestrict_service(service_id):
    service = get_service_by_id(service_id)
    service.restricted = False
    add_service(service)


def activate_service(service_id):
    service = get_service_by_id(service_id)
    service.active = True
    add_service(service)


def add_service(service):
    db.session.add(service)
    db.session.commit()


def find_service_by_service_name(service_name):
    return Service.query.filter_by(name=service_name).first()
