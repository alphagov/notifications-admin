from flask import has_request_context, session


def get_user_id_from_flask_login_session():
    if not has_request_context():
        return None

    # We don't check `current_user` here in order to avoid triggering authentication. Depending on where we put
    # log statements it could cause recursion and errors.
    # `session['_user_id'] is accessing part of Flask-Login internals so we may need to update this if the
    # internal mechanism changes.
    return session.get("_user_id", None)
