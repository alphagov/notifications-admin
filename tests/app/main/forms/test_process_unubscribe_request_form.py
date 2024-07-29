from app.main.forms import ProcessUnsubscribeRequestForm


def test_should_raise_validation_error_for_reports_whose_status_is_not_completed(
    client_request,
):
    form = ProcessUnsubscribeRequestForm(is_a_batched_report=True, report_completed=False)
    form.data["report_has_been_processed"] = False
    form.validate()
    assert form.validate() is False
    assert (
        "There is a problem. You must confirm that you have removed the email addresses from your mailing list."
        in form.errors["report_has_been_processed"]
    )


def test_should_raise_validation_error_for_resubmitting_marked_checkbox_for_an_already_completed_report(
    client_request,
):
    form = ProcessUnsubscribeRequestForm(
        is_a_batched_report=True, report_completed=True, report_has_been_processed=True
    )
    form.validate()
    assert form.validate() is False
    assert (
        "There is a problem. You have already marked the report as Completed"
        in form.errors["report_has_been_processed"]
    )


def test_should_raise_no_validation_error_for_reports_whose_status_is_being_changed_from_completed(
    client_request,
):
    """
    The test case covered, is that clearing a checkbox for a completed report, ie updating its status
    from "Completed" to "Downloaded", raises no validation errors.
    """
    form = ProcessUnsubscribeRequestForm(
        is_a_batched_report=True, report_completed=True, report_has_been_processed=False
    )
    assert form.validate() is True
