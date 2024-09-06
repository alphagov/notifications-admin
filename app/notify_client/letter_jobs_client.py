from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, cache


class LetterJobsClient(NotifyAdminAPIClient):
    @cache.delete_by_pattern("service-????????-????-????-????-????????????-returned-letters-statistics")
    @cache.delete_by_pattern("service-????????-????-????-????-????????????-returned-letters-summary")
    def submit_returned_letters(self, references):
        return self.post(url="/letters/returned", data={"references": references})


_letter_jobs_client_context_var: ContextVar[LetterJobsClient] = ContextVar("letter_jobs_client")
get_letter_jobs_client: LazyLocalGetter[LetterJobsClient] = LazyLocalGetter(
    _letter_jobs_client_context_var,
    lambda: LetterJobsClient(current_app),
)
memo_resetters.append(lambda: get_letter_jobs_client.clear())
letter_jobs_client = LocalProxy(get_letter_jobs_client)
