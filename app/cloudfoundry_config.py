"""
Extracts cloudfoundry config from its json and populates the environment variables that we would expect to be populated
on local/aws boxes
"""

import os
import json


def extract_cloudfoundry_config():
    vcap_services = json.loads(os.environ['VCAP_SERVICES'])

    set_config_env_vars(vcap_services)


def set_config_env_vars(vcap_services):
    vcap_application = json.loads(os.environ.get('VCAP_APPLICATION'))
    os.environ['NOTIFY_ENVIRONMENT'] = vcap_application['space_name']
    os.environ['NOTIFY_LOG_PATH'] = '/home/vcap/logs/app.log'

    for s in vcap_services['user-provided']:
        if s['name'] == 'notify-config':
            extract_notify_config(s)
        elif s['name'] == 'notify-aws':
            extract_notify_aws_config(s)
        elif s['name'] == 'hosted-graphite':
            extract_hosted_graphite_config(s)
        elif s['name'] == 'deskpro':
            extract_deskpro_config(s)
        elif s['name'] == 'notify-template-preview':
            extract_template_preview_config(s)


def extract_notify_config(notify_config):
    os.environ['ADMIN_CLIENT_SECRET'] = notify_config['credentials']['admin_client_secret']
    os.environ['API_HOST_NAME'] = notify_config['credentials']['api_host_name']
    os.environ['ADMIN_BASE_URL'] = notify_config['credentials']['admin_base_url']
    os.environ['SECRET_KEY'] = notify_config['credentials']['secret_key']
    os.environ['DANGEROUS_SALT'] = notify_config['credentials']['dangerous_salt']


def extract_notify_aws_config(aws_config):
    os.environ['AWS_ACCESS_KEY_ID'] = aws_config['credentials']['aws_access_key_id']
    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_config['credentials']['aws_secret_access_key']


def extract_hosted_graphite_config(hosted_graphite_config):
    os.environ['STATSD_PREFIX'] = hosted_graphite_config['credentials']['statsd_prefix']


def extract_deskpro_config(deskpro_config):
    os.environ['DESKPRO_API_HOST'] = deskpro_config['credentials']['api_host']
    os.environ['DESKPRO_API_KEY'] = deskpro_config['credentials']['api_key']


def extract_template_preview_config(template_preview_config):
    os.environ['TEMPLATE_PREVIEW_API_HOST'] = template_preview_config['credentials']['api_host']
    os.environ['TEMPLATE_PREVIEW_API_KEY'] = template_preview_config['credentials']['api_key']
