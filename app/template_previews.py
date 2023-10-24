import base64
from io import BytesIO

import requests
from flask import abort, current_app, json
from notifications_utils.pdf import extract_page_from_pdf

from app import current_service


class TemplatePreview:
    @staticmethod
    def get_allowed_headers(headers):
        header_allowlist = {"content-type", "cache-control"}
        allowed_headers = {header: value for header, value in headers.items() if header.lower() in header_allowlist}
        return allowed_headers.items()

    @classmethod
    def get_preview_for_templated_letter(cls, db_template, filetype, values=None, page=None):
        if db_template["is_precompiled_letter"]:
            abort(400)
        data = {
            "letter_contact_block": db_template.get("reply_to_text", ""),
            "template": db_template,
            "values": values,
            "filename": current_service.letter_branding.filename,
        }
        response = requests.post(
            "{}/preview.{}{}".format(
                current_app.config["TEMPLATE_PREVIEW_API_HOST"],
                filetype,
                "?page={}".format(page) if page else "",
            ),
            json=data,
            headers={"Authorization": f"Token {current_app.config['TEMPLATE_PREVIEW_API_KEY']}"},
        )
        return response.content, response.status_code, cls.get_allowed_headers(response.headers)

    @classmethod
    def get_png_for_valid_pdf_page(cls, pdf_file, page):
        pdf_page = extract_page_from_pdf(BytesIO(pdf_file), int(page) - 1)

        response = requests.post(
            "{}/precompiled-preview.png{}".format(
                current_app.config["TEMPLATE_PREVIEW_API_HOST"], "?hide_notify=true" if page == "1" else ""
            ),
            data=base64.b64encode(pdf_page).decode("utf-8"),
            headers={"Authorization": f"Token {current_app.config['TEMPLATE_PREVIEW_API_KEY']}"},
        )
        return response.content, response.status_code, cls.get_allowed_headers(response.headers)

    @classmethod
    def get_png_for_invalid_pdf_page(cls, pdf_file, page, is_an_attachment=False):
        pdf_page = extract_page_from_pdf(BytesIO(pdf_file), int(page) - 1)

        response = requests.post(
            "{}/precompiled/overlay.png{}".format(
                current_app.config["TEMPLATE_PREVIEW_API_HOST"],
                f"?page_number={page}&is_an_attachment={is_an_attachment}",
            ),
            data=pdf_page,
            headers={"Authorization": f"Token {current_app.config['TEMPLATE_PREVIEW_API_KEY']}"},
        )
        return response.content, response.status_code, cls.get_allowed_headers(response.headers)

    @classmethod
    def get_png_for_example_template(cls, template, branding_filename):
        data = {
            "letter_contact_block": template.get("reply_to_text"),
            "template": template,
            "values": None,
            "filename": branding_filename,
        }
        response = requests.post(
            f"{current_app.config['TEMPLATE_PREVIEW_API_HOST']}/preview.png",
            json=data,
            headers={"Authorization": f"Token {current_app.config['TEMPLATE_PREVIEW_API_KEY']}"},
        )
        return response.content, response.status_code, cls.get_allowed_headers(response.headers)

    @classmethod
    def get_png_for_letter_attachment_page(cls, attachment_id, page=None):
        data = {
            "letter_attachment_id": attachment_id,
            "service_id": current_service.id,
        }
        response = requests.post(
            "{}/letter_attachment_preview.png{}".format(
                current_app.config["TEMPLATE_PREVIEW_API_HOST"],
                "?page={}".format(page) if page else "",
            ),
            json=data,
            headers={"Authorization": f"Token {current_app.config['TEMPLATE_PREVIEW_API_KEY']}"},
        )
        return response.content, response.status_code, cls.get_allowed_headers(response.headers)


def get_page_count_for_letter(template, values=None):
    if template["template_type"] != "letter":
        return None

    page_count, _, _ = TemplatePreview.get_preview_for_templated_letter(template, "json", values)
    page_count = json.loads(page_count.decode("utf-8"))["count"]

    return page_count


def sanitise_letter(pdf_file, *, upload_id, allow_international_letters, is_an_attachment=False):
    url = "{host_url}/precompiled/sanitise?allow_international_letters={allow_intl}&upload_id={upload_id}".format(
        host_url=current_app.config["TEMPLATE_PREVIEW_API_HOST"],
        allow_intl="true" if allow_international_letters else "false",
        upload_id=upload_id,
    )
    if is_an_attachment:
        url = url + "&is_an_attachment=true"
    return requests.post(
        url,
        data=pdf_file,
        headers={"Authorization": f"Token {current_app.config['TEMPLATE_PREVIEW_API_KEY']}"},
    )
