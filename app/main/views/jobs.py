from flask import render_template

from app.main import main


messages = [
    {
        'phone': '+44 7700 900 579',
        'message': 'Vehicle tax: Your vehicle tax for LV75 TDG expires…',
        'status': 'Delivered',
        'time': '13:42',
        'id': '0'
    },
    {
        'phone': '+44 7700 900 306',
        'message': 'Vehicle tax: Your vehicle tax for PL53 GBD expires…',
        'status': 'Delivered',
        'time': '13:42',
        'id': '1'
    },
    {
        'phone': '+44 7700 900 454',
        'message': 'Vehicle tax: Your vehicle tax for LV75 TDG expires…',
        'status': 'Delivered',
        'time': '13:42',
        'id': '2'
    },
    {
        'phone': '+44 7700 900 522',
        'message': 'Vehicle tax: Your vehicle tax for RE67 PLM expires…',
        'status': 'Failed',
        'time': '13:42',
        'id': '3'
    }
]


@main.route("/jobs")
def showjobs():
    return render_template('views/jobs.html')


@main.route("/jobs/job/")
def showjob():
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
        cost='£0.00',
        uploaded_file_name='contact-demo.csv',
        template_used='Reminder template'
    )


@main.route("/jobs/job/notification/<string:notification_id>")
def shownotification(notification_id):
    return render_template(
        'views/notification.html',
        message=[
            message for message in messages if message['id'] == notification_id
        ][0]
    )
