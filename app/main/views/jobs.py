# -*- coding: utf-8 -*-

import time

from flask import (
    render_template,
    session
)
from flask_login import login_required

from app.main import main
from ._jobs import jobs

now = time.strftime('%H:%M')

messages = [
    {
        'phone': '+44 7700 900 579',
        'message': 'Vehicle tax: Your vehicle tax for LV75 TDG expires on 18 January 2016. Renew at www.gov.uk/vehicletax',  # noqa
        'status': 'Delivered',
        'time': now,
        'id': '0'
    },
    {
        'phone': '+44 7700 900 306',
        'message': 'Vehicle tax: Your vehicle tax for PL53 GBD expires on 18 January 2016. Renew at www.gov.uk/vehicletax',  # noqa
        'status': 'Delivered',
        'time': now,
        'id': '1'
    },
    {
        'phone': '+44 7700 900 454',
        'message': 'Vehicle tax: Your vehicle tax for LV75 TDG expires on 18 January 2016. Renew at www.gov.uk/vehicletax',  # noqa
        'status': 'Delivered',
        'time': now,
        'id': '2'
    },
    {
        'phone': '+44 7700 900 522',
        'message': 'Vehicle tax: Your vehicle tax for RE67 PLM expires on 18 January 2016. Renew at www.gov.uk/vehicletax',  # noqa
        'status': 'Failed',
        'time': now,
        'id': '3'
    }
]


@main.route("/services/<int:service_id>/jobs")
@login_required
def showjobs(service_id):
    return render_template(
        'views/jobs.html',
        jobs=jobs,
        service_id=service_id
    )


@main.route("/services/<int:service_id>/jobs/<job_id>")
@login_required
def showjob(service_id, job_id):

    # TODO the uploaded file name could be part of job definition
    # so won't need to be passed on from last view via session
    uploaded_file_name = session.get(job_id)

    return render_template(
        'views/job.html',
        messages=messages,
        counts={
            'total': len(messages),
            'delivered': len([
                message for message in messages if message['status'] == 'Delivered'
            ]),
            'failed': len([
                message for message in messages if message['status'] == 'Failed'
            ])
        },
        cost=u'£0.00',
        uploaded_file_name=uploaded_file_name,
        uploaded_file_time=now,
        template_used='Test message 1',
        flash_message=u'We’ve started sending your messages',
        service_id=service_id
    )


@main.route("/services/<int:service_id>/jobs/<job_id>/notification/<string:notification_id>")
@login_required
def shownotification(service_id, job_id, notification_id):
    return render_template(
        'views/notification.html',
        message=[
            message for message in messages if message['id'] == notification_id
        ][0],
        delivered_at=now,
        uploaded_at=now,
        service_id=service_id,
        job_id=job_id
    )
