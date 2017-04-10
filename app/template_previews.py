from flask import current_app, current_service
import requests


def get_template_preview(template, filetype):
    data = {
        "letter_contact_block": current_service['letter_contact_block'],
        "admin_base_url": current_app.config['ADMIN_BASE_URL'],
        "template": template,
        "values": None
    }
    resp = requests.post(
        '{}/preview.{}'.format(current_app.config['TEMPLATE_PREVIEW_SERVICE_URL'], filetype),
        json=data,
        headers={'Authorization': 'Token my-secret-key'}
    )
    return (resp.content, resp.status_code, resp.headers.items())
