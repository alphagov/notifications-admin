from flask import jsonify

from app.status import status


@status.route('/_status')
def status():
    from app import (get_app_version, status_api_client)
    api_status = 'n/a'
    try:
        api_status = status_api_client.get_status()
    except:
        api_status = 'n/a'
    return jsonify(status="ok",
                   app_version=get_app_version(),
                   api_status=api_status), 200
