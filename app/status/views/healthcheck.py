from flask import jsonify, request, current_app
from app import (version, status_api_client)
from app.status import status
from notifications_python_client.errors import HTTPError


@status.route('/_status', methods=['GET'])
def show_status():
    if request.args.get('elb', None):
        return jsonify(status="ok"), 200
    else:
        try:
            api_status = status_api_client.get_status()
        except HTTPError as e:
            current_app.logger.exception("API failed to respond")
            return jsonify(status="error", message=str(e.message)), 500
        return jsonify(
            status="ok",
            api=api_status,
            travis_commit=version.__travis_commit__,
            travis_build_number=version.__travis_job_number__,
            build_time=version.__time__), 200
