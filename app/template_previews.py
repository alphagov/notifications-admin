import base64
import uuid
from io import BytesIO

import requests
from flask import abort, current_app, json, request
from flask.ctx import has_request_context
from notifications_utils.pdf import extract_page_from_pdf

from app import current_service


class TemplatePreview:
    @staticmethod
    def get_allowed_headers(headers):
        header_allowlist = {"content-type", "cache-control"}
        allowed_headers = {header: value for header, value in headers.items() if header.lower() in header_allowlist}
        return allowed_headers.items()

    @classmethod
    def _get_outbound_headers(cls):
        headers = {"Authorization": f"Token {current_app.config['TEMPLATE_PREVIEW_API_KEY']}"}
        if has_request_context() and hasattr(request, "get_onwards_request_headers"):
            headers.update(request.get_onwards_request_headers())
        return headers

    @classmethod
    def get_preview_for_templated_letter(
        cls,
        db_template,
        filetype,
        values=None,
        page=None,
        branding_filename=None,
        cache_key=None,
    ):
        """
        Arguments:
        - db_template: template object, as serialized from the db
        - filetype: png or pdf - we want preview as png to show on the page, and preview as pdf for users to download
        - page: only important for png preview, page number we want previewed as png
        - branding_filename: name of letter branding file to use for the letter
        - cache_key: one of the following:
            - template id + version (for templates), or
            - notification id (for notifications), or
            - template id + version + hash of personalisation (for template with filled in placeholders, in review step)
            - fixed uuid + branding filename (for preview on letter branding journeys)
        """
        if db_template["is_precompiled_letter"]:
            raise ValueError
        if db_template["template_type"] != "letter":
            abort(404)
        if filetype == "pdf" and page:
            abort(400)
        data = {
            "letter_contact_block": db_template.get("reply_to_text", ""),
            "template": db_template,
            "values": values,
            "filename": branding_filename or (current_service.letter_branding.filename if current_service else None),
            "cache_key": cache_key or "random-" + uuid.uuid4(),
        }
        response = requests.post(
            "{}/preview.{}{}".format(
                current_app.config["TEMPLATE_PREVIEW_API_HOST"],
                filetype,
                "?page={}".format(page) if page else "",
            ),
            json=data,
            headers=cls._get_outbound_headers(),
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
            headers=cls._get_outbound_headers(),
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
            headers=cls._get_outbound_headers(),
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
            headers=cls._get_outbound_headers(),
        )
        return response.content, response.status_code, cls.get_allowed_headers(response.headers)

    @classmethod
    def get_page_counts_for_letter(cls, db_template, values=None):
        """
        Expected return value format (mimics the template-preview endpoint:
            {'count': int, 'welsh_page_count': int, 'attachment_page_count': int}
        """
        if db_template["template_type"] != "letter":
            return None

        data = {
            "letter_contact_block": db_template.get("reply_to_text", ""),
            "template": db_template,
            "values": values,
            "filename": current_service.letter_branding.filename,
        }
        response = requests.post(
            f"{current_app.config['TEMPLATE_PREVIEW_API_HOST']}/preview.json".format(),
            json=data,
            headers=cls._get_outbound_headers(),
        )

        page_count = json.loads(response.content.decode("utf-8"))

        return page_count

    @classmethod
    def sanitise_letter(cls, pdf_file, *, upload_id, allow_international_letters, is_an_attachment=False):
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
            headers=cls._get_outbound_headers(),
        )
