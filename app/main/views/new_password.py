from flask import request

from app.main import main


@main.route('/new-password/<token>', methods=['GET', 'POST'])
def new_password():
    # Validate token
    token = request.args.get('token')
    # get password token (better name)
    # is it expired
    # add NewPasswordForm
    # update password
    # create password_token table (id, token, user_id, expiry_date

    return 'Got here'
