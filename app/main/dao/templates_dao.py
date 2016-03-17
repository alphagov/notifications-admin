from flask import url_for
from app import service_api_client
from app.utils import BrowsableItem


def insert_service_template(name, type_, content, service_id, subject=None):
    return service_api_client.create_service_template(
        name, type_, content, service_id, subject)


def update_service_template(id_, name, type_, content, service_id, subject=None):
    return service_api_client.update_service_template(
        id_, name, type_, content, service_id)


def get_service_templates(service_id):
    return service_api_client.get_service_templates(service_id)


def get_service_template_or_404(service_id, template_id):
    return service_api_client.get_service_template(service_id, template_id)


def delete_service_template(service_id, template_id):
    return service_api_client.delete_service_template(
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
