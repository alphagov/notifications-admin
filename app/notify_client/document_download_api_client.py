import base64
from abc import ABC, abstractmethod
from contextvars import ContextVar

import requests
from flask import current_app, has_request_context, request
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters


class DocumentDownloadError(Exception):
    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code

    @classmethod
    def from_exception(cls, e: requests.RequestException, status_code: int | None = None):
        if e.response is None:
            raise ValueError("RequestException has no response") from e

        resolved_status_code = status_code or e.response.status_code

        if resolved_status_code == 413:
            message = "The file must be smaller than 2MB"
        else:
            message = e.response.json().get("error", None)

        return cls(message, resolved_status_code)


class AbstractDocumentDownloadClient(ABC):
    """
    This will enforce uniformity of methods between the DocumentDownloadClient and the MockDocumentDownloadAPIClient
    """

    @abstractmethod
    def file_check_and_antivirus_scan(self, service_id: str, file_name: str, file_bytes: bytes) -> dict:
        pass


class DocumentDownloadAPIClient(AbstractDocumentDownloadClient):
    # This connection pool will be created once when the module loads and will be used across the instances
    request_session = requests.Session()

    def __init__(self, app):
        self.base_url = app.config["DOCUMENT_DOWNLOAD_API_HOST_NAME_INTERNAL"]
        self.auth_token = app.config["DOCUMENT_DOWNLOAD_API_KEY"]

    def file_check_and_antivirus_scan(self, service_id, file_name, file_bytes):
        """
        This method runs file validation checks and an antivirus scan and also determines the file mimetype
        """
        file_check_url = f"{self.base_url}/services/{service_id}/antivirus-and-mimetype-check"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        file_data = {"document": base64.b64encode(file_bytes).decode("utf-8"), "filename": file_name}

        if has_request_context() and hasattr(request, "get_onwards_request_headers"):
            headers.update(request.get_onwards_request_headers())

        try:
            response = self.request_session.post(
                file_check_url,
                headers=headers,
                json=file_data,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            # we want to specifically handle 400 (virus scan failed, file type unrecognised or file name too long)
            #  and 413 (file too big).
            if e.response is None:
                raise Exception(f"Unhandled document download error: {repr(e)}") from e
            elif e.response.status_code in {400, 413}:
                error = DocumentDownloadError.from_exception(e, status_code=e.response.status_code)
                current_app.logger.info("Document download request failed with error: %s", error.message)
                raise error from e
            else:
                raise Exception(f"Unhandled document download error: {e.response.text}") from e

        return response.json()


_document_download_api_client_context_var: ContextVar[DocumentDownloadAPIClient] = ContextVar(
    "document_download_api_client"
)
get_document_download_api_client: LazyLocalGetter[DocumentDownloadAPIClient] = LazyLocalGetter(
    _document_download_api_client_context_var,
    lambda: DocumentDownloadAPIClient(current_app),
)
memo_resetters.append(lambda: get_document_download_api_client.clear())
document_download_api_client = LocalProxy(get_document_download_api_client)
