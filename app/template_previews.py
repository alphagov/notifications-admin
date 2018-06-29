from io import BytesIO

import requests
from flask import current_app, json

from app import current_service


class TemplatePreview:
    @classmethod
    def from_database_object(cls, template, filetype, values=None, page=None):
        data = {
            'letter_contact_block': template.get('reply_to_text', ''),
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


def get_page_count_for_letter(template, values=None):

    if template['template_type'] != 'letter':
        return None

    page_count, _, _ = TemplatePreview.from_database_object(template, 'json', values)
    page_count = json.loads(page_count.decode('utf-8'))['count']

    return page_count


def get_letter_logos():
    response = requests.get(
        '{}/logos.json'.format(
            current_app.config['TEMPLATE_PREVIEW_API_HOST'],
        ),
        headers={'Authorization': 'Token {}'.format(current_app.config['TEMPLATE_PREVIEW_API_KEY'])}
    )
    return json.loads(response.content)


def get_letter_logo_file(filename):
    response = requests.get(
        '{}/static/images/letter-template/{}'.format(
            current_app.config['TEMPLATE_PREVIEW_API_HOST'],
            filename
        ),
        headers={'Authorization': 'Token {}'.format(current_app.config['TEMPLATE_PREVIEW_API_KEY'])}
    )
    return BytesIO(response.content)
