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
    build, build_time = get_api_version()
    return jsonify(status="ok",
                   app_version=get_app_version(),
                   api_build=build,
                   api_built_time=build_time), 200
