from flask import render_template, url_for, redirect
from app.main import main
from flask_login import login_required

from flask.ext.login import current_user


@main.route('/')
def index():
    if current_user and current_user.is_authenticated():
        return redirect(url_for('main.choose_service'))
    return render_template('views/signedout.html')


@main.route("/register-from-invite")
@login_required
def register_from_invite():
    return render_template('views/register-from-invite.html')


@main.route("/verify-mobile")
@login_required
def verify_mobile():
    return render_template('views/verify-mobile.html')


@main.route("/services/<service_id>/send-email")
@login_required
def send_email(service_id):
    return render_template('views/send-email.html', service_id=service_id)


@main.route("/services/<service_id>/check-email")
@login_required
def check_email(service_id):
    return render_template('views/check-email.html')


@main.route("/services/<service_id>/manage-users")
@login_required
def manage_users(service_id):
    users = [
        {
            'name': 'Henry Hadlow',
            'permission_send_messages': True,
            'permission_manage_service': False,
            'permission_manage_api_keys': False
        },

        {
            'name': 'Pete Herlihy',
            'permission_send_messages': False,
            'permission_manage_service': False,
            'permission_manage_api_keys': False,
        },
        {
            'name': 'Chris Hill-Scott',
            'permission_send_messages': True,
            'permission_manage_service': True,
            'permission_manage_api_keys': True
        },
        {
            'name': 'Martyn Inglis',
            'permission_send_messages': True,
            'permission_manage_service': True,
            'permission_manage_api_keys': True
        }
    ]
    invited_users = [
        {
            'email_localpart': 'caley.smolska',
            'permission_send_messages': True,
            'permission_manage_service': False,
            'permission_manage_api_keys': False
        },

        {
            'email_localpart': 'ash.stephens',
            'permission_send_messages': False,
            'permission_manage_service': False,
            'permission_manage_api_keys': False
        },
        {
            'email_localpart': 'nicholas.staples',
            'permission_send_messages': True,
            'permission_manage_service': True,
            'permission_manage_api_keys': True
        },
        {
            'email_localpart': 'adam.shimali',
            'permission_send_messages': True,
            'permission_manage_service': True,
            'permission_manage_api_keys': True
        }
    ]
    return render_template('views/manage-users.html', service_id=service_id, users=users, invited_users=invited_users)
