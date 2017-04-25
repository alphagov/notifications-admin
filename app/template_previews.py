from flask import current_app
import requests

from app import current_service


class TemplatePreview:
    @classmethod
    def from_database_object(cls, template, filetype, values=None, page=None):
        data = {
            'letter_contact_block': current_service['letter_contact_block'],
            'template': template,
            'values': values,
            'dvla_org_id': current_service['dvla_organisation'],
        }
        resp = requests.post(
            '{}/preview.{}{}'.format(
                current_app.config['TEMPLATE_PREVIEW_API_HOST'],
                filetype,
                '?page={}'.format(page) if page else '',
            ),
            json=data,
            headers={'Authorization': 'Token {}'.format(current_app.config['TEMPLATE_PREVIEW_API_KEY'])}
        )
        return (resp.content, resp.status_code, resp.headers.items())

    @classmethod
    def from_utils_template(cls, template, filetype, page=None):
        return cls.from_database_object(
            template._template,
            filetype,
            template.values,
            page=page,
        )
