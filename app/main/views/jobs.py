from flask import (
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from markupsafe import Markup
from notifications_python_client.errors import HTTPError
from notifications_utils.recipients import RecipientCSV

from app import (
    current_service,
    format_datetime_short,
    format_thousands,
)
from app.formatters import get_time_left, message_count_noun
from app.main import json_updates, main
from app.models.job import Job
from app.notify_client.job_api_client import JobApiClient
from app.s3_client.s3_csv_client import s3download
from app.utils import parse_filter_args, set_status_filters
from app.utils.csv import generate_notifications_csv
from app.utils.letters import get_letter_printing_statement, printing_today_or_tomorrow
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/jobs")
@user_has_permissions()
def view_jobs(service_id):
    return redirect(
        url_for(
            "main.uploads",
            service_id=current_service.id,
        )
    )


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>")
@user_has_permissions()
def view_job(service_id, job_id):
    job = Job.from_id(job_id, service_id=current_service.id)
    if job.cancelled:
        abort(404)

    filter_args = parse_filter_args(request.args)
    filter_args["status"] = set_status_filters(filter_args)

    just_sent_message = "Your {} been sent. Printing starts {} at 5:30pm.".format(
        "letter has" if job.notification_count == 1 else "letters have", printing_today_or_tomorrow(job.created_at)
    )

    if job.scheduled:
        scheduled_recipients = RecipientCSV(
            s3download(current_service.id, job.id),
            template=current_service.get_template(job.template_id),
            max_initial_rows_shown=50,
        )
    else:
        scheduled_recipients = None

    return render_template(
        "views/jobs/job.html",
        job=job,
        status=request.args.get("status", ""),
        updates_url=url_for(
            "json_updates.view_job_updates",
            service_id=service_id,
            job_id=job.id,
            status=request.args.get("status", ""),
        ),
        partials=get_job_partials(job),
        just_sent=request.args.get("just_sent") == "yes",
        just_sent_message=just_sent_message,
        scheduled_recipients=scheduled_recipients,
    )


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>.csv")
@user_has_permissions("view_activity")
def view_job_csv(service_id, job_id):
    job = Job.from_id(job_id, service_id=service_id)
    filter_args = parse_filter_args(request.args)
    filter_args["status"] = set_status_filters(filter_args)

    data = generate_notifications_csv(
        service_id=service_id,
        job_id=job_id,
        status=filter_args.get("status"),
        page=request.args.get("page", 1),
        page_size=5000,
        template_type=job.template_type,
    )
    return Response(
        list(data),
        mimetype="text/csv",
        headers={
            "Content-Disposition": 'inline; filename="{} - {}.csv"'.format(
                job.template["name"], format_datetime_short(job.created_at)
            )
        },
    )


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>/original.csv")
@user_has_permissions("view_activity")
def view_job_original_file_csv(service_id, job_id):
    job = Job.from_id(job_id, service_id=service_id)

    if not job.scheduled:
        abort(404)

    original_file_contents = s3download(current_service.id, job.id)

    return Response(
        original_file_contents,
        mimetype="text/csv",
        headers={"Content-Disposition": f'inline; filename="{job.original_file_name_without_extention}.csv"'},
    )


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>", methods=["POST"])
@user_has_permissions("send_messages")
def cancel_job(service_id, job_id):
    Job.from_id(job_id, service_id=service_id).cancel()
    return redirect(url_for("main.service_dashboard", service_id=service_id))


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>/cancel", methods=["GET", "POST"])
@user_has_permissions()
def cancel_letter_job(service_id, job_id):
    if request.method == "POST":
        job = Job.from_id(job_id, service_id=service_id)

        # reduce to just == FINISHED_ALL_NOTIFICATIONS_CREATED_JOB_STATUS once api support rolled out
        if job.status not in JobApiClient.FINISHED_JOB_STATUSES or job.notifications_created < job.notification_count:
            flash("We are still processing these letters, please try again in a minute.", "try again")
            return view_job(service_id, job_id)
        try:
            number_of_letters = job.cancel()
        except HTTPError as e:
            flash(e.message, "dangerous")
            return redirect(url_for("main.view_job", service_id=service_id, job_id=job_id))
        flash(
            f"Cancelled {format_thousands(number_of_letters)} letters from {job.original_file_name}",
            "default_with_tick",
        )
        return redirect(url_for("main.service_dashboard", service_id=service_id))

    flash("Are you sure you want to cancel sending these letters?", "cancel")
    return view_job(service_id, job_id)


@json_updates.route("/services/<uuid:service_id>/jobs/<uuid:job_id>.json")
@user_has_permissions()
def view_job_updates(service_id, job_id):
    job = Job.from_id(job_id, service_id=service_id)

    return jsonify(**get_job_partials(job))


def _get_job_counts(job):
    job_type = job.template_type
    return [
        (
            label,
            query_param,
            url_for(
                "main.view_job",
                service_id=job.service,
                job_id=job.id,
                status=query_param,
            ),
            count,
        )
        for label, query_param, count in [
            [
                Markup(
                    f"""total<span class="govuk-visually-hidden">
                    {"text message" if job_type == "sms" else job_type}s</span>"""
                ),
                "",
                job.notification_count,
            ],
            [
                Markup(
                    f"""delivering<span class="govuk-visually-hidden">
                    {message_count_noun(job.notifications_sending, job_type)}</span>"""
                ),
                "sending",
                job.notifications_sending,
            ],
            [
                Markup(
                    f"""delivered<span class="govuk-visually-hidden">
                    {message_count_noun(job.notifications_delivered, job_type)}</span>"""
                ),
                "delivered",
                job.notifications_delivered,
            ],
            [
                Markup(
                    f"""failed<span class="govuk-visually-hidden">
                    {message_count_noun(job.notifications_failed, job_type)}</span>"""
                ),
                "failed",
                job.notifications_failed,
            ],
        ]
    ]


def get_job_partials(job):
    filter_args = parse_filter_args(request.args)
    filter_args["status"] = set_status_filters(filter_args)
    notifications = job.get_notifications(status=filter_args["status"])
    if job.template_type == "letter":
        counts = render_template(
            "partials/jobs/count-letters.html",
            job=job,
        )
    else:
        counts = render_template(
            "partials/count.html",
            counts=_get_job_counts(job),
            status=filter_args["status"],
            notifications_deleted=(job.status == "finished" and not notifications),
        )
    service_data_retention_days = current_service.get_days_of_retention(job.template_type)

    return {
        "counts": counts,
        "notifications": render_template(
            "partials/jobs/notifications.html",
            notifications=notifications,
            more_than_one_page=notifications.next,
            download_link=url_for(
                "main.view_job_csv", service_id=current_service.id, job_id=job.id, status=request.args.get("status")
            ),
            time_left=get_time_left(job.created_at, service_data_retention_days=service_data_retention_days),
            job=job,
            service_data_retention_days=service_data_retention_days,
        ),
        "status": render_template(
            "partials/jobs/status.html",
            job=job,
            letter_print_day=get_letter_printing_statement("created", job.created_at),
        ),
    }
