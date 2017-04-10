from flask import current_app
import requests

from app import current_service


class TemplatePreview:
    @classmethod
    def from_database_object(cls, template, filetype, values=None):
        data = {
            "letter_contact_block": current_service['letter_contact_block'],
            "admin_base_url": current_app.config['ADMIN_BASE_URL'],
            "template": template,
            "values": values
        }
        resp = requests.post(
            '{}/preview.{}'.format(current_app.config['TEMPLATE_PREVIEW_SERVICE_URL'], filetype),
            json=data,
            headers={'Authorization': 'Token my-secret-key'}
        )
        return (resp.content, resp.status_code, resp.headers.items())

    @classmethod
    def from_utils_template(cls, template, filetype):
        return cls.from_database_object(
            template._template,
            filetype,
            template.values
        )
