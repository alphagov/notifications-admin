from datetime import datetime

from flask import render_template, url_for
from werkzeug.utils import redirect

from app import provider_client
from app.main import main
from app.main.forms import AdminProviderRatioForm
from app.utils.user import user_is_platform_admin

PROVIDER_PRIORITY_MEANING_SWITCHOVER = datetime(2019, 11, 29, 11, 0).isoformat()


@main.route("/providers")
@user_is_platform_admin
def view_providers():
    providers = provider_client.get_all_providers()['provider_details']
    domestic_email_providers, domestic_sms_providers, intl_sms_providers = [], [], []
    for provider in providers:
        if provider['notification_type'] == 'sms':
            domestic_sms_providers.append(provider)
            if provider.get('supports_international', None):
                intl_sms_providers.append(provider)
        elif provider['notification_type'] == 'email':
            domestic_email_providers.append(provider)

    add_monthly_traffic(domestic_sms_providers)

    return render_template(
        'views/providers/providers.html',
        email_providers=domestic_email_providers,
        domestic_sms_providers=domestic_sms_providers,
        intl_sms_providers=intl_sms_providers
    )


def add_monthly_traffic(domestic_sms_providers):
    total_sms_sent = sum(provider['current_month_billable_sms'] for provider in domestic_sms_providers)

    for provider in domestic_sms_providers:
        percentage = (provider['current_month_billable_sms'] / total_sms_sent * 100) if total_sms_sent else 0
        provider['monthly_traffic'] = round(percentage)


@main.route("/provider/edit-sms-provider-ratio", methods=['GET', 'POST'])
@user_is_platform_admin
def edit_sms_provider_ratio():
    providers = [
        provider
        for provider in provider_client.get_all_providers()['provider_details']
        if provider['notification_type'] == 'sms' and provider['active']
    ]

    form = AdminProviderRatioForm(providers)

    if form.validate_on_submit():
        for provider in providers:
            field = getattr(form, provider['identifier'])
            provider_client.update_provider(provider['id'], field.data)
        return redirect(url_for('.view_providers'))

    return render_template(
        'views/providers/edit-sms-provider-ratio.html',
        form=form,
        providers=providers
    )


@main.route("/provider/<uuid:provider_id>")
@user_is_platform_admin
def view_provider(provider_id):
    versions = provider_client.get_provider_versions(provider_id)
    return render_template('views/providers/provider.html', provider_versions=versions['data'])
