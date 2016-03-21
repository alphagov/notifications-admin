from flask import url_for, current_app
from app import service_api_client
from app.utils import BrowsableItem


def update_service(service):
    return service_api_client.update_service(
        service['id'],
        service['name'],
        service['active'],
        service['limit'],
        service['restricted'],
        service['users'])


def get_service_by_id(id_):
    return service_api_client.get_service(id_)


def get_service_by_id_or_404(id_):
    return service_api_client.get_service(id_)['data']


def get_services(user_id=None):
    if user_id:
        return service_api_client.get_services({'user_id': str(user_id)})
    else:
        return service_api_client.get_services()


def unrestrict_service(service_id):
    resp = service_api_client.get_service(service_id)
    if resp['data']['restricted']:
        resp = service_api_client.update_service(
            service_id,
            resp['data']['name'],
            resp['data']['active'],
            resp['data']['limit'],
            False,
            resp['data']['users'])


def activate_service(service_id):
    resp = service_api_client.get_service(service_id)
    if not resp['data']['active']:
        resp = service_api_client.update_service(
            service_id,
            resp['data']['name'],
            True,
            resp['data']['limit'],
            resp['data']['restricted'],
            resp['data']['users'])


# TODO Fix when functionality is added to the api.
def find_service_by_service_name(service_name, user_id=None):
    resp = service_api_client.get_services(user_id)
    retval = None
    for srv_json in resp['data']:
        if srv_json['name'] == service_name:
            retval = srv_json
            break
    return retval


def delete_service(id_):
    return service_api_client.delete_service(id_)


def find_all_service_names(user_id=None):
    resp = service_api_client.get_services(user_id)
    return [x['name'] for x in resp['data']]


class ServicesBrowsableItem(BrowsableItem):

    @property
    def title(self):
        return self._item['name']

    @property
    def link(self):
        return url_for('main.service_dashboard', service_id=self._item['id'])

    @property
    def destructive(self):
        return False

    @property
    def hint(self):
        return None
