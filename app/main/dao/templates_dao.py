from flask import url_for, abort
from app import notifications_api_client
from app.utils import BrowsableItem
from notifications_python_client.errors import HTTPError


def insert_service_template(name, type_, content, service_id, subject=None):
    return notifications_api_client.create_service_template(
        name, type_, content, service_id, subject)


def update_service_template(id_, name, type_, content, service_id, subject=None):
    return notifications_api_client.update_service_template(
        id_, name, type_, content, service_id)


def get_service_templates(service_id):
    return notifications_api_client.get_service_templates(service_id)


def get_service_template_or_404(service_id, template_id):
    try:
        return notifications_api_client.get_service_template(service_id, template_id)
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e


def delete_service_template(service_id, template_id):
    return notifications_api_client.delete_service_template(
        service_id, template_id)


class TemplatesBrowsableItem(BrowsableItem):

    @property
    def title(self):
        return self._item['name']

    @property
    def type(self):
        return self._item['template_type']

    @property
    def link(self):
        return url_for(
            'main.edit_service_template',
            service_id=self._item['service'],
            template_id=self._item['id'])

    @property
    def destructive(self):
        return False

    @property
    def hint(self):
        return "Some service template hint here"

    def get_field(self, field):
        return self._item.get(field, None)
