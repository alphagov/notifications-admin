from collections import defaultdict
from datetime import datetime
from operator import itemgetter

from flask import abort, render_template, url_for
from werkzeug.utils import redirect

from app import format_date_numeric, provider_client
from app.main import main
from app.main.forms import AdminProviderForm, AdminProviderRatioForm
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


@main.route("/provider/<uuid:provider_id>/edit", methods=['GET', 'POST'])
@user_is_platform_admin
def edit_provider(provider_id):
    provider = provider_client.get_provider_by_id(provider_id)['provider_details']
    form = AdminProviderForm(active=provider['active'], priority=provider['priority'])

    if form.validate_on_submit():
        provider_client.update_provider(provider_id, form.priority.data)
        return redirect(url_for('.view_providers'))

    return render_template('views/providers/edit-provider.html', form=form, provider=provider)


@main.route("/provider/edit-sms-provider-ratio", methods=['GET', 'POST'])
@user_is_platform_admin
def edit_sms_provider_ratio():

    providers = sorted([
        provider
        for provider in provider_client.get_all_providers()['provider_details']
        if provider['notification_type'] == 'sms'
        and provider['active']
    ], key=itemgetter('identifier'))

    form = AdminProviderRatioForm(ratio=providers[0]['priority'])

    if len(providers) < 2:
        abort(400)

    primary_provider, secondary_provider = providers[0:2]

    if form.validate_on_submit():
        provider_client.update_provider(primary_provider['id'], form.percentage_left)
        provider_client.update_provider(secondary_provider['id'], form.percentage_right)
        return redirect(url_for('.edit_sms_provider_ratio'))

    return render_template(
        'views/providers/edit-sms-provider-ratio.html',
        versions=_chunk_versions_by_day(_get_versions_since_switchover(primary_provider['id'])),
        form=form,
        primary_provider=providers[0]['display_name'],
        secondary_provider=providers[1]['display_name'],
    )


def _get_versions_since_switchover(provider_id):

    for version in sorted(
        provider_client.get_provider_versions(provider_id)['data'],
        key=lambda version: version['updated_at'] or ''
    ):

        if not version['updated_at']:
            continue

        if version['updated_at'] < PROVIDER_PRIORITY_MEANING_SWITCHOVER:
            continue

        yield version


def _chunk_versions_by_day(versions):

    days = defaultdict(list)

    for version in sorted(versions, key=lambda version: version['updated_at'] or '', reverse=True):
        days[
            format_date_numeric(version['updated_at'])
        ].append(version)

    return sorted(days.items(), reverse=True)


@main.route("/provider/<uuid:provider_id>")
@user_is_platform_admin
def view_provider(provider_id):
    versions = provider_client.get_provider_versions(provider_id)
    return render_template('views/providers/provider.html', provider_versions=versions['data'])
