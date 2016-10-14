from flask_login import current_user


def _attach_current_user(data):
    return dict(
        created_by=current_user.id,
        **data
    )
