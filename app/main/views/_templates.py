templates = [
    {
        'type': 'sms',
        'name': 'Confirmation',
        'body': 'Lasting power of attorney: We’ve received your application. Applications take between 8 and 10 weeks to process.'  # noqa
    },
    {
        'type': 'sms',
        'name': 'Reminder',
        'body': 'Vehicle tax: Your vehicle tax for ((registration number)) expires on ((date)). Tax your vehicle at www.gov.uk/vehicle-tax'  # noqa
    },
    {
        'type': 'sms',
        'name': 'Warning',
        'body': 'Vehicle tax: Your vehicle tax for ((registration number)) has expired. Tax your vehicle at www.gov.uk/vehicle-tax'  # noqa
    },
    {
        'type': 'email',
        'name': 'Application alert 06/2016',
        'subject': 'Your lasting power of attorney application',
        'body': """Dear ((name)),

When you’ve made your lasting power of attorney (LPA), you need to register it \
with the Office of the Public Guardian (OPG).

You can apply to register your LPA yourself if you’re able to make your own decisions.

Your attorney can also register it for you. You’ll be told if they do and you can \
object to the registration.

It takes between 8 and 10 weeks to register an LPA if there are no mistakes in the application.
        """
    },
    {
        'type': 'sms',
        'name': 'Air quality alert',
        'body': 'Air pollution levels will be ((level)) in ((region)) tomorrow.'
    },
]
