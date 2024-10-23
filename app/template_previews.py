import base64
from contextvars import ContextVar
from io import BytesIO

import requests
from flask import abort, current_app, json, request
from flask.ctx import has_request_context
from notifications_utils.local_vars import LazyLocalGetter
from notifications_utils.pdf import extract_page_from_pdf
from werkzeug.local import LocalProxy

from app import memo_resetters


class TemplatePreviewClient:
    requests_session: requests.Session
    api_key: str
    api_host: str

    def __init__(self, app):
        self.requests_session = requests.Session()
        self.api_key = app.config["TEMPLATE_PREVIEW_API_KEY"]
        self.api_host = app.config["TEMPLATE_PREVIEW_API_HOST"]

    @staticmethod
    def get_allowed_headers(headers):
        header_allowlist = {"content-type", "cache-control"}
        allowed_headers = {header: value for header, value in headers.items() if header.lower() in header_allowlist}
        return allowed_headers.items()

    def _get_outbound_headers(self):
        headers = {"Authorization": f"Token {self.api_key}"}
        if has_request_context() and hasattr(request, "get_onwards_request_headers"):
            headers.update(request.get_onwards_request_headers())
        return headers

    def get_preview_for_templated_letter(
        self,
        db_template,
        filetype,
        values=None,
        page=None,
        branding_filename=None,
        service=None,
    ):
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
            "filename": branding_filename or (service.letter_branding.filename if service else None),
        }
        response = self.requests_session.post(
            "{}/preview.{}{}".format(
                self.api_host,
                filetype,
                f"?page={page}" if page else "",
            ),
            json=data,
            headers=self._get_outbound_headers(),
        )
        return response.content, response.status_code, self.get_allowed_headers(response.headers)

    def get_png_for_valid_pdf_page(self, pdf_file, page):
        pdf_page = extract_page_from_pdf(BytesIO(pdf_file), int(page) - 1)

        response = self.requests_session.post(
            "{}/precompiled-preview.png{}".format(self.api_host, "?hide_notify=true" if page == "1" else ""),
            data=base64.b64encode(pdf_page).decode("utf-8"),
            headers=self._get_outbound_headers(),
        )
        return response.content, response.status_code, self.get_allowed_headers(response.headers)

    def get_png_for_invalid_pdf_page(self, pdf_file, page, is_an_attachment=False):
        pdf_page = extract_page_from_pdf(BytesIO(pdf_file), int(page) - 1)

        response = self.requests_session.post(
            "{}/precompiled/overlay.png{}".format(
                self.api_host,
                f"?page_number={page}&is_an_attachment={is_an_attachment}",
            ),
            data=pdf_page,
            headers=self._get_outbound_headers(),
        )
        return response.content, response.status_code, self.get_allowed_headers(response.headers)

    def get_png_for_letter_attachment_page(self, attachment_id, service, page=None):
        data = {
            "letter_attachment_id": attachment_id,
            "service_id": service.id,
        }
        response = self.requests_session.post(
            "{}/letter_attachment_preview.png{}".format(
                self.api_host,
                f"?page={page}" if page else "",
            ),
            json=data,
            headers=self._get_outbound_headers(),
        )
        return response.content, response.status_code, self.get_allowed_headers(response.headers)

    def get_page_counts_for_letter(self, db_template, service, values=None):
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
            "filename": service.letter_branding.filename,
        }
        response = self.requests_session.post(
            f"{self.api_host}/get-page-count",
            json=data,
            headers=self._get_outbound_headers(),
        )

        page_count = json.loads(response.content.decode("utf-8"))

        return page_count

    def sanitise_letter(self, pdf_file, *, upload_id, allow_international_letters, is_an_attachment=False):
        url = "{host_url}/precompiled/sanitise?allow_international_letters={allow_intl}&upload_id={upload_id}".format(
            host_url=self.api_host,
            allow_intl="true" if allow_international_letters else "false",
            upload_id=upload_id,
        )
        if is_an_attachment:
            url = url + "&is_an_attachment=true"
        return self.requests_session.post(
            url,
            data=pdf_file,
            headers=self._get_outbound_headers(),
        )


_template_preview_client_context_var: ContextVar[TemplatePreviewClient] = ContextVar("template_preview_client")
get_template_preview_client: LazyLocalGetter[TemplatePreviewClient] = LazyLocalGetter(
    _template_preview_client_context_var,
    lambda: TemplatePreviewClient(current_app),
)
memo_resetters.append(lambda: get_template_preview_client.clear())
template_preview_client = LocalProxy(get_template_preview_client)
