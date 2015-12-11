from flask import request, render_template, redirect, url_for
from flask_login import login_required

from app.main import main


@main.route("/sms/send", methods=['GET', 'POST'])
def sendsms():
    if request.method == 'GET':
        return render_template(
            'views/send-sms.html',
            message_templates=[
                {
                    'name': 'Reminder',
                    'body': """
                        Vehicle tax: Your vehicle tax for ((registration number)) expires on ((date)).
                        Tax your vehicle at www.gov.uk/vehicle-tax
                    """
                },
                {
                    'name': 'Warning',
                    'body': """
                        Vehicle tax: Your vehicle tax for ((registration number)) has expired.
                        Tax your vehicle at www.gov.uk/vehicle-tax
                    """
                },
            ]
        )
    elif request.method == 'POST':
        return redirect(url_for('.checksms'))


@main.route("/sms/check", methods=['GET', 'POST'])
def checksms():
    if request.method == 'GET':
        return render_template(
            'views/check-sms.html',
            recipients=[
                {'phone': "+44 7700 900989", 'registration number': 'LC12 BFL', 'date': '24 December 2015'},
                {'phone': "+44 7700 900479", 'registration number': 'DU04 AOM', 'date': '25 December 2015'},
                {'phone': "+44 7700 900964", 'registration number': 'M91 MJB', 'date': '26 December 2015'},
                {'phone': "+44 7700 900703", 'registration number': 'Y249 NPU', 'date': '31 December 2015'},
                {'phone': "+44 7700 900730", 'registration number': 'LG55 UGB', 'date': '1 January 2016'}
            ],
            message_template="""
                Vehicle tax: Your vehicle tax for ((registration number)) expires on ((date)).
                Tax your vehicle at www.gov.uk/vehicle-tax
            """
        )
    elif request.method == 'POST':
        return redirect(url_for('.showjob'))
