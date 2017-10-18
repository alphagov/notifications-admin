from flask import render_template
from flask_login import login_required
from app.main import main
from app import inbound_number_client
from app.utils import user_has_permissions


@main.route('/inbound-sms-admin', methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
def inbound_sms_admin():
    data = inbound_number_client.get_all_inbound_sms_number_service()

    return render_template('views/inbound-sms-admin.html', inbound_num_list=data)
