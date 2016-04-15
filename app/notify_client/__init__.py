from flask.ext.login import current_user


def _attach_current_user(data):
    data['created_by'] = current_user.id
    return data
